import os
from pathlib import Path
from datetime import datetime
from smolagents import InferenceClientModel, CodeAgent, AgentGenerationError
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import Any, Optional

from planner import generate_research_plan
from task_splitter import split_into_subtasks
from firecrawl_tools import search_web, scrape_url
from utils.config_loader import ConfigLoader
from utils.prompt_loader import PromptLoader

config = ConfigLoader.load()
# coordinator_prompt_template = PromptLoader.load("coordinator_prompt_template.md")
subagent_prompt_template = PromptLoader.load("subagent_prompt_template.md")
synthesis_prompt_template = PromptLoader.load("synthesis_prompt_template.md")

FIRECRAWL_API_KEY = os.environ["FIRECRAWL_API_KEY"]
MCP_URL = f"https://mcp.firecrawl.dev/{FIRECRAWL_API_KEY}/v2/mcp"

COORDINATOR_MODEL_ID = config["COORDINATOR"]["MODEL_ID"]
COORDINATOR_PROVIDER = config["COORDINATOR"]["PROVIDER"]
SUBAGENT_MODEL_ID    = config["SUBAGENT"]["MODEL_ID"]
SUBAGENT_PROVIDER    = config["SUBAGENT"]["PROVIDER"]


def run_with_retries(agent: Any, prompt: str, max_retries: int = 3, base_delay: float = 5.0,) -> Any:
    """
    Run `agent.run(prompt)` with retries and exponential backoff.

    Args:
        agent: An object exposing a `run(prompt: str) -> Any` method.
        prompt: The prompt string passed to `agent.run`.
        max_retries: Maximum number of attempts before failing. Must be >= 1.
        base_delay: Base delay in seconds used to compute backoff. Must be > 0.

    Returns:
        The value returned by `agent.run(prompt)` on the first successful attempt.

    Raises:
        ValueError: If `max_retries` < 1 or `base_delay` <= 0.
        RuntimeError: If all attempts fail; the last exception is attached as the cause.
    """
    if max_retries < 1:
        raise ValueError("max_retries must be >= 1")
    if base_delay <= 0:
        raise ValueError("base_delay must be > 0")

    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Attempt {attempt}/{max_retries}")
            return agent.run(prompt)
        except AgentGenerationError as exc:
            last_error = exc

            # Exponential backoff: base_delay * 2^(attempt-1)
            delay_seconds = base_delay * (2 ** (attempt - 1))

            if attempt < max_retries:
                print(
                    "Model generation failed (attempt "
                    f"{attempt}/{max_retries}). Retrying in {delay_seconds:.1f}s..."
                )
                time.sleep(delay_seconds)

    raise RuntimeError(f"Failed after {max_retries} attempts") from last_error


def run_deep_research(user_query: str) -> str:
    print("Running the deep research...")

    # 1) Generate research plan
    research_plan = generate_research_plan(user_query)

    # 2) Split into explicit subtasks
    subtasks = split_into_subtasks(research_plan)

    # 3) Coordinator + sub-agents, all sharing the Firecrawl MCP tools
    print("Initializing Coordinator")
    print("Coordinator Model: ", COORDINATOR_MODEL_ID)
    print("Subagent Model: ", SUBAGENT_MODEL_ID)

    coordinator_model = InferenceClientModel(
        model_id=COORDINATOR_MODEL_ID, 
        api_key=os.environ["HF_TOKEN"],
        provider=COORDINATOR_PROVIDER,
        )
    subagent_model = InferenceClientModel(
        model_id=SUBAGENT_MODEL_ID, 
        api_key=os.environ["HF_TOKEN"],
        provider=SUBAGENT_PROVIDER,
        )
    
    # Firecrawl MCP tools
    firecrawl_tools = [search_web, scrape_url]

    # ---- Run single subagent (for concurrent execution) ----------------
    def run_subagent(subtask: dict) -> dict:
        """Run a single subagent and return its result with metadata."""
        subtask_id = subtask["id"]
        subtask_title = subtask["title"]
        subtask_description = subtask["description"]

        print(f"[Subagent {subtask_id}] Starting...")

        subagent = CodeAgent(
            tools=firecrawl_tools,
            model=subagent_model,
            add_base_tools=False,
            name=f"subagent_{subtask_id}",
            # max_steps=5,
        )

        subagent_prompt = subagent_prompt_template.format(
            user_query=user_query,
            research_plan=research_plan,
            subtask_id=subtask_id,
            subtask_title=subtask_title,
            subtask_description=subtask_description,
        )

        result = subagent.run(subagent_prompt)
        print(f"[Subagent {subtask_id}] Completed")

        return {
            "id": subtask_id,
            "title": subtask_title,
            "result": result
        }

    # ---- Run all subagents concurrently --------------------------------
    print(f"Running {len(subtasks)} subagents concurrently...")
    subagent_results = []

    with ThreadPoolExecutor(max_workers=len(subtasks)) as executor:
        futures = {executor.submit(run_subagent, subtask): subtask for subtask in subtasks}

        for future in as_completed(futures):
            subtask = futures[future]
            try:
                result = future.result()
                subagent_results.append(result)
            except Exception as e:
                print(f"[Subagent {subtask['id']}] Failed: {e}")
                subagent_results.append({
                    "id": subtask["id"],
                    "title": subtask["title"],
                    "result": f"Error: {str(e)}"
                })

    # Sort results by subtask ID to maintain consistent order
    subagent_results.sort(key=lambda x: x["id"])

    # ---- Synthesize results with chief editor agent -------------------
    print("Synthesizing results with chief editor agent...")

    # Combine all subagent reports
    combined_reports = "\n\n---\n\n".join([
        f"## Subtask: {r['title']} (ID: {r['id']})\n\n{r['result']}"
        for r in subagent_results
    ])

    synthesis_prompt = synthesis_prompt_template.format(
        user_query=user_query,
        research_plan=research_plan,
        combined_reports=combined_reports,
    )

    # Create chief editor agent with web search tools for validation
    chief_editor = CodeAgent(
        tools=firecrawl_tools,
        model=coordinator_model,
        add_base_tools=False,
        name="chief_editor",
    )

    # final_report = chief_editor.run(synthesis_prompt)
    final_report = run_with_retries(
        agent=chief_editor,
        prompt=synthesis_prompt,
        max_retries=3,
        base_delay=10,
    )

    # ---- Save final report and subagent reports ------------------------
    reports_base_dir = Path("reports")
    reports_base_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = reports_base_dir / timestamp
    report_dir.mkdir(exist_ok=True)
    
    # Save final report
    final_report_path = report_dir / "final_report.md"
    with open(final_report_path, "w", encoding="utf-8") as f:
        f.write(final_report)
    
    # Save subagent reports
    subagents_dir = report_dir / "subagents"
    subagents_dir.mkdir(exist_ok=True)
    
    for result in subagent_results:
        subagent_filename = f"{result['id']}_{result['title'].replace(' ', '_').lower()}.md"
        subagent_path = subagents_dir / subagent_filename
        with open(subagent_path, "w", encoding="utf-8") as f:
            f.write(f"# {result['title']}\n\n")
            f.write(f"**Subtask ID:** {result['id']}\n\n")
            f.write("---\n\n")
            f.write(result['result'])
    
    print(f"Final report saved to: {final_report_path}")
    print(f"Subagent reports saved to: {subagents_dir}")

    return final_report
