import os
from huggingface_hub import InferenceClient
from utils.config_loader import ConfigLoader
from utils.prompt_loader import PromptLoader

config = ConfigLoader.load()
planner_system_instructions = PromptLoader.load("planner_system_instructions.md")

def generate_research_plan(user_query: str) -> str:
    MODEL_ID = config["PLANNER"]["MODEL_ID"]
    PROVIDER = config["PLANNER"]["PROVIDER"]

    planner_client = InferenceClient(
        api_key=os.environ["HF_TOKEN"],
        provider=PROVIDER,
    )

    completion = planner_client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": planner_system_instructions},
            {"role": "user", "content": user_query},
        ],
        # If you want to stream the response, set stream to True.
        # When false, the full response is returned once complete.
        stream=False,
    )

    print("\033[93mGenerated Research Plan:\033[0m")
    #research_plan = completion.choices[0].message.content
    research_plan = ""
    
    def _content(obj):
        try:
            return obj.choices[0].delta.content
        except Exception:
            try:
                return obj.choices[0].message.content
            except Exception:
                return None

    try:
        for chunk in completion:
            c = _content(chunk)
            if c:
                research_plan += c
                print(c, end="")
    except TypeError:
        c = _content(completion)
        if c:
            research_plan = c
            print(c, end="")

    return research_plan