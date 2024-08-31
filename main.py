from libs.core.types import (
    Task,
    Metadata,
    TaskSpec,
    BaseTaskOutput,
    ReactOutput,
    ReactAnswer,
)
from openai import OpenAI
from libs.core.engine import exec_task, exec_react_task
from libs.core.contexts import cli_ctx, react_ctx
import sys

task = Task(
    metadata=Metadata(
        name="list the files in the current directory",
        apiVersion="v1",
    ),
    spec=TaskSpec(
        input={},
        contexts=[cli_ctx, react_ctx],
        instruction=sys.argv[1],
        response_model=ReactOutput,
    ),
)

print(exec_react_task(OpenAI(), task, ask=True))
# print(exec_task(OpenAI(), task))
# print(exec_react_task(OpenAI(), task, ask=True).data)
