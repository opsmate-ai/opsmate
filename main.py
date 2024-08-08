from libs.core.types import *
from typing import List, Iterable
from openai import OpenAI
import instructor
from pydantic import create_model
import inspect
from inspect import Parameter
from libs.core.engine import exec_task
from libs.core.contexts import cli_ctx

# os_cli_tool = Tool(
#     metadata=Metadata(
#         name="cli", apiVersion="v1", labels={"type": "system"}, description="System CLI"
#     ),
#     spec=ToolSpec(
#         params={},
#         contexts=[os_ctx],
#         instruction="you are a sysadmin specialised in OS commands",
#     ),
# )


class TaskOutput(BaseModel):
    data: str = Field(title="output of the task")


task = Task(
    metadata=Metadata(
        name="list the files in the current directory",
        apiVersion="v1",
    ),
    spec=TaskSpec(
        input={},
        contexts=[cli_ctx],
        instruction="count loc in the current directory",
        response_model=TaskOutput,
    ),
)

exec_task(OpenAI(), task)
