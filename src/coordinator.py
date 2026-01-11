import os
import json
from planner import generate_research_plan
from task_splitter import split_into_subtasks
from utils.config_loader import ConfigLoader
from utils.prompt_loader import PromptLoader
from smolagents import LiteLLMModel, ToolCallingAgent, MCPClient, tool, InferenceClientModel

config = ConfigLoader.load()
coordinator_prompt_template = PromptLoader.load("coordinator_prompt_template.md")
subagent_prompt_template = PromptLoader.load("subagent_prompt_template.md")

FIRECRAWL_API_KEY = os.environ["FIRECRAWL_API_KEY"]
MCP_URL = f"https://mcp.firecrawl.dev/{FIRECRAWL_API_KEY}/v2/mcp"

COORDINATOR_MODEL_ID = config["COORDINATOR"]["MODEL_ID"]
COORDINATOR_PROVIDER = config["COORDINATOR"]["PROVIDER"]
SUBAGENT_MODEL_ID    = config["SUBAGENT"]["MODEL_ID"]
SUBAGENT_PROVIDER    = config["SUBAGENT"]["PROVIDER"]

def run_deep_research(user_query: str) -> str:
    print("Running the deep research...")

    # 1) Generate research plan
    research_plan = generate_research_plan(user_query)
    assert isinstance(research_plan, str), type(research_plan)

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

    with MCPClient({"url": MCP_URL, "transport": "streamable-http"}) as mcp_tools:

        # ---- Initialize Subagent TOOL --------------------------------------
        @tool
        def initialize_subagent(subtask_id: str, subtask_title: str, subtask_description: str) -> str:
            """
           Spawn a dedicated research sub-agent for a single subtask.

            Args:
                subtask_id (str): The unique identifier for the subtask.
                subtask_title (str): The descriptive title of the subtask.
                subtask_description (str): Detailed instructions for the sub-agent to perform the subtask.

            The sub-agent:
            - Has access to the Firecrawl MCP tools.
            - Must perform deep research ONLY on this subtask.
            - Returns a structured markdown report with:
              - a clear heading identifying the subtask,
              - a narrative explanation,
              - bullet-point key findings,
              - explicit citations / links to sources.
            """
            print(f"Initializing Subagent for task {subtask_id}...")

            subagent = ToolCallingAgent(
                tools=mcp_tools,                # Firecrawl MCP toolkit
                model=subagent_model,
                add_base_tools=False,
                name=f"subagent_{subtask_id}",
            )

            subagent_prompt = subagent_prompt_template.format(
                user_query=user_query,
                research_plan=research_plan,
                subtask_id=subtask_id,
                subtask_title=subtask_title,
                subtask_description=subtask_description,
            )
            
            return subagent.run(subagent_prompt)

        # ---- Initialize Coordinator agent ---------------------------------------------
        coordinator = ToolCallingAgent(
            tools=[initialize_subagent],
            model=coordinator_model,
            add_base_tools=False,
            name="coordinator_agent",
        )

        # Coordinator prompt: it gets the list of subtasks and the tool
        subtasks_json = json.dumps(subtasks, indent=2, ensure_ascii=False)

        coordinator_prompt = coordinator_prompt_template.format(
            user_query=user_query,
            research_plan=research_plan,
            subtasks_json=subtasks_json,
        )

        final_report = coordinator.run(coordinator_prompt)
        return final_report