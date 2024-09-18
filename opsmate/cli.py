from opsmate.libs.core.types import (
    Task,
    Metadata,
    TaskSpec,
    ReactOutput,
)
from openai import OpenAI
from opsmate.libs.core.engine import exec_react_task
from opsmate.libs.core.contexts import cli_ctx, react_ctx
from opsmate.libs.core.trace import traceit
from openai_otel import OpenAIAutoInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
import os
import click

resource = Resource(attributes={SERVICE_NAME: os.getenv("SERVICE_NAME", "opamate")})
provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
    insecure=True,
)
processor = BatchSpanProcessor(exporter)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)


OpenAIAutoInstrumentor().instrument()


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
@traceit
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
@traceit
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
@traceit
def chat(ask, model, max_depth):
    try:
        click.echo(
            """
OpsMate: Howdy! How can I help you?

Some useful commands:

!clear - Clear the chat history
!exit - Exit the chat
"""
        )
        historic_context = []
        while True:
            user_input = click.prompt("You")

            if user_input == "!clear":
                historic_context = []
                click.echo("OpsMate: Chat history cleared")
                continue
            elif user_input == "!exit":
                break

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
    except click.exceptions.Abort:
        click.echo("OpsMate: Goodbye!")


if __name__ == "__main__":
    opsmate_cli()
