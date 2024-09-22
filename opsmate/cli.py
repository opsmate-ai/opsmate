from opsmate.libs.core.types import (
    Task,
    Metadata,
    TaskSpec,
    ReactOutput,
    ReactProcess,
    ReactAnswer,
    ExecResult,
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
from rich.console import Console
from rich.table import Table
from rich.text import Text
import sys
import subprocess
import threading

console = Console()
resource = Resource(attributes={SERVICE_NAME: os.getenv("SERVICE_NAME", "opamate")})

otel_enabled = os.getenv("OTEL_ENABLED", "false").lower() == "true"

if otel_enabled:
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
@traceit
def install_playwright():
    """
    Install Playwright
    """
    # get the current python path
    python_path = sys.executable

    console.print("Installing Playwright", style="yellow")

    process = subprocess.Popen(
        [python_path, "-m", "playwright", "install", "chromium"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    def read_output(stream, output):
        for line in stream:
            output.write(line)
            output.flush()

    stdout_thread = threading.Thread(
        target=read_output, args=(process.stdout, sys.stdout)
    )
    stderr_thread = threading.Thread(
        target=read_output, args=(process.stderr, sys.stderr)
    )

    stdout_thread.start()
    stderr_thread.start()

    stdout_thread.join()
    stderr_thread.join()

    process.wait()

    console.print("Playwright installed successfully", style="green")


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
@click.option(
    "--answer-only",
    is_flag=True,
    help="Only show the answer and not the thought, action and observation",
)
@traceit
def run(instruction, ask, model, max_depth, answer_only):
    """
    Run a task with the OpsMate.
    """
    q_and_a(
        instruction, ask=ask, model=model, max_depth=max_depth, answer_only=answer_only
    )


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
        console.print(model_name)


help_msg = """
Commands:

!clear - Clear the chat history
!exit - Exit the chat
!help - Show this message
"""


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
@click.option(
    "--answer-only",
    is_flag=True,
    help="Only show the answer and not the thought, action and observation",
)
@traceit
def chat(ask, model, max_depth, answer_only):
    try:
        opsmate_says("Howdy! How can I help you?\n" + help_msg)

        historic_context = []
        while True:
            # user_input = click.prompt("You")
            user_input = console.input("[bold cyan]You> [/bold cyan]")
            if user_input == "!clear":
                historic_context = []
                opsmate_says("Chat history cleared")
                continue
            elif user_input == "!exit":
                break
            elif user_input == "!help":
                console.print(help_msg)
                continue

            q_and_a(
                user_input,
                ask=ask,
                max_depth=max_depth,
                model=model,
                historic_context=historic_context,
                answer_only=answer_only,
            )
    except (KeyboardInterrupt, EOFError):
        opsmate_says("Goodbye!")


@traceit(exclude=["historic_context"])
def q_and_a(
    user_input: str,
    ask: bool = False,
    max_depth: int = 10,
    model: str = "gpt-4o",
    historic_context: list = [],
    answer_only: bool = False,
):
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
        for output in exec_react_task(
            OpenAI(),
            task,
            ask=ask,
            max_depth=max_depth,
            model=model,
            historic_context=historic_context,
        ):
            if isinstance(output, ReactAnswer):
                opsmate_says(output.answer)
            elif isinstance(output, ReactProcess) and not answer_only:
                table = Table(title="OpsMate", show_header=True, show_lines=True)
                table.add_row("Question", output.question)
                table.add_row("Thought", output.thought)
                table.add_row("Action", output.action)
                console.print(table)

            elif isinstance(output, ExecResult) and not answer_only:
                table = Table(title="OpsMate", show_header=True, show_lines=True)
                table.add_column("Command", style="cyan")
                table.add_column("Stdout", style="green")
                table.add_column("Stderr", style="red")
                table.add_column("Exit Code", style="magenta")
                for call in output.calls:
                    table.add_row(
                        call.command,
                        call.output.stdout,
                        call.output.stderr,
                        str(call.output.exit_code),
                    )
                console.print(table)
    except Exception as e:
        console.print(f"OpsMate Error: {e}", style="red")


def opsmate_says(message: str):
    text = Text()
    text.append("OpsMate> ", style="bold green")
    text.append(message)
    console.print(text)


if __name__ == "__main__":
    opsmate_cli()
