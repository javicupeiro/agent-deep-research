import os
import json
from typing import List
from pydantic import BaseModel, Field

from huggingface_hub import InferenceClient
from utils.config_loader import ConfigLoader
from utils.prompt_loader import PromptLoader

config = ConfigLoader.load()
task_splitter_system_instructions = PromptLoader.load("task_splitter_system_instructions.md")

class Subtask(BaseModel):
    id: str = Field(
        ...,
        description="Short identifier for the subtask (e.g. 'A', 'history', 'drivers').",
    )
    title: str = Field(
        ...,
        description="Short descriptive title of the subtask.",
    )
    description: str = Field(
        ...,
        description="Clear, detailed instructions for the sub-agent that will research this subtask.",
    )

class SubtaskList(BaseModel):
    subtasks: List[Subtask] = Field(
        ...,
        description="List of subtasks that together cover the whole research plan.",
    )

TASK_SPLITTER_JSON_SCHEMA = {
    "name": "subtaskList",
    "schema": SubtaskList.model_json_schema(),
    "strict": True,
}

def split_into_subtasks(research_plan: str) -> List[Subtask]:

    MODEL_ID = config["SPLITTER"]["MODEL_ID"]
    PROVIDER = config["SPLITTER"]["PROVIDER"]

    print("Splitting the research plan into subtasks...")
    print("MODEL: ", MODEL_ID)
    print("PROVIDER: ", PROVIDER)
    
    client = InferenceClient(
        api_key=os.environ["HF_TOKEN"],
        provider=PROVIDER,
    )
    completion = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": task_splitter_system_instructions},
            {"role": "user", "content": research_plan},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": TASK_SPLITTER_JSON_SCHEMA,
        }
    )

    message = completion.choices[0].message

    subtasks = json.loads(message.content)['subtasks']

    print("\033[93mGenerated The Following Subtasks\033[0m")
    for task in subtasks:
      print(f"\033[93m{task['title']}\033[0m")
      print(f"\033[93m{task['description']}\033[0m")
      print()
    return subtasks