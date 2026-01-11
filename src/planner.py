import os
import yaml
from pathlib import Path
from huggingface_hub import InferenceClient
from prompts import PLANNER_SYSTEM_INSTRUCTIONS

from pathlib import Path
import yaml

def load_config():
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config" / "dev.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def generate_research_plan(user_query: str) -> str:
    config = load_config()
    MODEL_ID = config["PLANNER"]["MODEL_ID"]
    PROVIDER = config["PLANNER"]["PROVIDER"]

    planner_client = InferenceClient(
        api_key=os.environ["HF_TOKEN"],
        provider=PROVIDER,
    )

    return planner_client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": user_query},
        ],
        # If you want to stream the response, set stream to True.
        # When false, the full response is returned once complete.
        stream=True,
    )
