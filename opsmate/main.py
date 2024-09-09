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


@click.group()
def opsmate_cli():
    """
    OpsMate is an SRE AI assistant that helps you manage production environment.
    This is the cli tool to interact with OpsMate.
    """
    pass


@opsmate_cli.command()
@click.argument("instruction")
@click.option(
    "--ask", is_flag=True, help="Ask for confirmation before executing commands"
)
@click.option(
    "--model",
    default="gpt-4o",
    help="OpenAI model to use. To list models available please run the list-models command.",
)
@click.option(
    "--max-depth",
    default=10,
    help="Max depth the AI assistant can reason about",
)
def ask(instruction, ask, model, max_depth):
    """
    Ask a question to the OpsMate.
    """
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

    answer, _ = exec_react_task(
        OpenAI(), task, ask=ask, model=model, max_depth=max_depth
    )
    click.echo(answer)


@opsmate_cli.command()
def list_models():
    """
    List all the models available in OpenAI.
    """
    client = OpenAI()
    model_names = [
        model.id for model in client.models.list().data if model.id.startswith("gpt")
    ]
    for model_name in model_names:
        print(model_name)


@opsmate_cli.command()
@click.option(
    "--ask", is_flag=True, help="Ask for confirmation before executing commands"
)
@click.option(
    "--model",
    default="gpt-4o",
    help="OpenAI model to use. To list models available please run the list-models command.",
)
@click.option(
    "--max-depth",
    default=10,
    help="Max depth the AI assistant can reason about",
)
def chat(ask, model, max_depth):
    click.echo("OpsMate: Howdy! How can I help you?")
    historic_context = []
    while True:
        user_input = click.prompt("You")
        task = Task(
            metadata=Metadata(
                name="chat",
                apiVersion="v1",
            ),
            spec=TaskSpec(
                input={},
                contexts=[cli_ctx, react_ctx],
                instruction=user_input,
                response_model=ReactOutput,
            ),
        )

        try:
            answer, historic_context = exec_react_task(
                OpenAI(),
                task,
                ask=ask,
                historic_context=historic_context,
                max_depth=max_depth,
                model=model,
            )
        except Exception as e:
            click.echo(f"OpsMate: {e}")
            continue
        click.echo(f"OpsMate: {answer}")


if __name__ == "__main__":
    opsmate_cli()
