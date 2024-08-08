from libs.core.types import Task, Metadata, TaskSpec
from pydantic import BaseModel, Field
from openai import OpenAI
from libs.core.engine import exec_task
from libs.core.contexts import cli_ctx


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
        instruction="what's the current operating system name and version",
        response_model=TaskOutput,
    ),
)

print(exec_task(OpenAI(), task).data)
