from libs.core.types import Task, Metadata, TaskSpec, BaseTaskOutput
from openai import OpenAI
from libs.core.engine import exec_task
from libs.core.contexts import cli_ctx
import sys

task = Task(
    metadata=Metadata(
        name="list the files in the current directory",
        apiVersion="v1",
    ),
    spec=TaskSpec(
        input={},
        contexts=[cli_ctx],
        instruction=sys.argv[1],
        response_model=BaseTaskOutput,
    ),
)

print(exec_task(OpenAI(), task, ask=True).data)
