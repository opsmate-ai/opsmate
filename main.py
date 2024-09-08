from libs.core.types import (
    Task,
    Metadata,
    TaskSpec,
    ReactOutput,
)
from openai import OpenAI
from libs.core.engine import exec_task, exec_react_task
from libs.core.contexts import cli_ctx, react_ctx
import click


@click.command()
@click.argument("instruction")
@click.option(
    "--ask", is_flag=True, help="Ask for confirmation before executing commands"
)
def main(instruction, ask):
    task = Task(
        metadata=Metadata(
            name=instruction,
            apiVersion="v1",
        ),
        spec=TaskSpec(
            input={},
            contexts=[cli_ctx, react_ctx],
            instruction=instruction,
            response_model=ReactOutput,
        ),
    )

    print(exec_react_task(OpenAI(), task, ask=ask))


if __name__ == "__main__":
    main()
