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
from rich.markdown import Markdown
import structlog
import logging
from opsmate.dino import dino, run_react
from opsmate.dino.types import Observation, ReactAnswer, React, Message
from opsmate.tools import ShellCommand
import asyncio
from functools import wraps


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


loglevel = os.getenv("LOGLEVEL", "ERROR").upper()
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelNamesMapping()[loglevel]
    ),
)
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

logger = structlog.get_logger(__name__)


@click.group()
def opsmate_cli():
    """
    OpsMate is an SRE AI assistant that helps you manage production environment.
    This is the cli tool to interact with OpsMate.
    """
    pass


@dino("gpt-4o", response_model=Observation, tools=[ShellCommand])
async def run_command(instruction: str, model: str = "gpt-4o"):
    """
    You are a world class SRE who is good at comes up with shell commands with given instructions.
    """

    return instruction


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
@traceit
@coro
async def run(instruction, ask, model):
    """
    Run a task with the OpsMate.
    """
    logger.info("Running on", instruction=instruction, model=model)

    observation = await run_command(instruction, model=model)

    for tool_call in observation.tool_outputs:
        console.print(Markdown(tool_call.markdown()))

    console.print(Markdown(observation.observation))


@opsmate_cli.command()
@click.argument("instruction")
@click.option(
    "--model",
    default="gpt-4o",
    help="OpenAI model to use. To list models available please run the list-models command.",
)
@click.option(
    "--max-iter",
    default=10,
    help="Max number of iterations the AI assistant can reason about",
)
@click.option(
    "--context",
    default="You are a helpful SRE who has access to a terminal",
    help="Context to be added to the prompt",
)
@traceit
@coro
async def solve(instruction, model, max_iter, context):
    """
    Solve a problem with the OpsMate.
    """
    async for output in run_react(
        instruction,
        context=context,
        model=model,
        max_iter=max_iter,
        tools=[ShellCommand],
    ):
        if isinstance(output, React):
            console.print(
                Markdown(
                    f"""
## Thought process
### Thought

{output.thoughts}

### Action

{output.action}
"""
                )
            )
        elif isinstance(output, ReactAnswer):
            console.print(
                Markdown(
                    f"""
## Answer

{output.answer}
"""
                )
            )
        elif isinstance(output, Observation):
            console.print(Markdown("## Observation"))
            for tool_call in output.tool_outputs:
                console.print(Markdown(tool_call.markdown()))
            console.print(Markdown(output.observation))


help_msg = """
Commands:

!clear - Clear the chat history
!exit - Exit the chat
!help - Show this message
"""


@opsmate_cli.command()
@click.option(
    "--model",
    default="gpt-4o",
    help="OpenAI model to use. To list models available please run the list-models command.",
)
@click.option(
    "--max-iter",
    default=10,
    help="Max number of iterations the AI assistant can reason about",
)
@click.option(
    "--context",
    default="You are a helpful SRE who has access to a terminal",
    help="Context to add to the prompt",
)
@traceit
@coro
async def chat(model, max_iter, context):
    """
    Chat with the OpsMate.
    """

    opsmate_says("Howdy! How can I help you?\n" + help_msg)

    chat_history = []
    while True:
        user_input = console.input("[bold cyan]You> [/bold cyan]")
        if user_input == "!clear":
            chat_history = []
            opsmate_says("Chat history cleared")
            continue
        elif user_input == "!exit":
            break
        elif user_input == "!help":
            console.print(help_msg)
            continue

        run = run_react(
            user_input,
            context=context,
            model=model,
            max_iter=max_iter,
            tools=[ShellCommand],
            chat_history=chat_history,
        )
        chat_history.append(Message.user(user_input))

        try:
            async for output in run:
                if isinstance(output, React):
                    tp = f"""
## Thought process
### Thought

{output.thoughts}

### Action

{output.action}
"""
                    console.print(Markdown(tp))
                    chat_history.append(Message.assistant(tp))
                elif isinstance(output, ReactAnswer):
                    tp = f"""
## Answer

{output.answer}
"""
                    console.print(Markdown(tp))
                    chat_history.append(Message.assistant(tp))
                elif isinstance(output, Observation):
                    tp = f"""##Observation
### Tool outputs
"""
                    for tool_call in output.tool_outputs:
                        tp += f"""
    {tool_call.markdown()}
    """
                    tp += f"""
### Observation

{output.observation}
"""
                    console.print(Markdown(tp))
                    chat_history.append(Message.assistant(tp))
        except (KeyboardInterrupt, EOFError):
            opsmate_says("Goodbye!")


def opsmate_says(message: str):
    text = Text()
    text.append("OpsMate> ", style="bold green")
    text.append(message)
    console.print(text)


if __name__ == "__main__":
    opsmate_cli()
