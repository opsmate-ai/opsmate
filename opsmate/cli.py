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
from opsmate.dino.provider import Provider
from opsmate.contexts import contexts
import asyncio
from functools import wraps
from opsmate.plugins import PluginRegistry


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


def common_params(func):
    @click.option("--tools", default="")
    @wraps(func)
    def wrapper(*args, **kwargs):
        PluginRegistry.discover(os.getenv("OPSMATE_TOOLS_DIR", "./tools"))
        _tool_names = kwargs.pop("tools")
        _tool_names = _tool_names.split(",")
        _tool_names = [t for t in _tool_names if t != ""]
        try:
            tools = PluginRegistry.get_tools_from_list(_tool_names)
        except ValueError as e:
            console.print(
                f"Tool {e} not found. Run the list-tools command to see all the tools available."
            )
            exit(1)

        kwargs["tools"] = tools

        return func(*args, **kwargs)

    return wrapper


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
    "--context",
    default="cli",
    help="Context to be added to the prompt. Run the list-contexts command to see all the contexts available.",
)
@common_params
@traceit
@coro
# async def run(instruction, ask, model, context):
async def run(instruction, ask, model, context, tools):
    """
    Run a task with the OpsMate.
    """

    ctx = get_context(context)

    if len(tools) == 0:
        tools = ctx.tools

    logger.info("Running on", instruction=instruction, model=model)

    @dino("gpt-4o", response_model=Observation, tools=tools)
    async def run_command(instruction: str):
        return [
            Message.system(ctx.ctx()),
            Message.user(instruction),
        ]

    observation = await run_command(instruction)

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
    default="cli",
    help="Context to be added to the prompt. Run the list-contexts command to see all the contexts available.",
)
@common_params
@traceit
@coro
async def solve(instruction, model, max_iter, context, tools):
    """
    Solve a problem with the OpsMate.
    """
    ctx = get_context(context)

    if len(tools) == 0:
        tools = ctx.tools

    async for output in run_react(
        instruction,
        contexts=[Message.system(ctx.ctx())],
        model=model,
        max_iter=max_iter,
        tools=tools,
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
    default="cli",
    help="Context to be added to the prompt. Run the list-contexts command to see all the contexts available.",
)
@common_params
@traceit
@coro
async def chat(model, max_iter, context, tools):
    """
    Chat with the OpsMate.
    """

    ctx = get_context(context)

    if len(tools) == 0:
        tools = ctx.tools

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
            contexts=[Message.system(ctx.ctx())],
            model=model,
            max_iter=max_iter,
            tools=tools,
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


@opsmate_cli.command()
def list_contexts():
    """
    List all the contexts available.
    """
    table = Table(title="Contexts", show_header=True)
    table.add_column("Context")
    table.add_column("Description")

    for ctx_name, ctx in contexts.items():
        table.add_row(ctx_name, ctx.description)

    console.print(table)


@opsmate_cli.command()
@click.option("--host", default="0.0.0.0", help="Host to serve on")
@click.option("--port", default=8080, help="Port to serve on")
@coro
async def serve(host, port):
    """
    Start the OpsMate server.
    """
    from opsmate.apiserver.apiserver import app
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port)
    server = uvicorn.Server(config)
    await server.serve()


@opsmate_cli.command()
def list_tools():
    """
    List all the tools available.
    """
    PluginRegistry.discover(os.getenv("OPSMATE_TOOLS_DIR", "./tools"))

    table = Table(title="Tools", show_header=True, show_lines=True)
    table.add_column("Tool")
    table.add_column("Description")

    for tool_name, tool in PluginRegistry.get_tools().items():
        table.add_row(tool_name, tool.__doc__)

    console.print(table)


@opsmate_cli.command()
def list_models():
    """
    List all the models available.
    """
    table = Table(title="Models", show_header=True, show_lines=True)
    table.add_column("Provider")
    table.add_column("Model")

    for provider_name, provider in Provider.providers.items():
        for model in provider.models:
            table.add_row(provider_name, model)

    console.print(table)


def get_context(ctx_name: str):
    ctx = contexts.get(ctx_name)
    if not ctx:
        console.print(
            f"Context {ctx_name} not found. Run the list-contexts command to see all the contexts available."
        )
        exit(1)
    return ctx


def opsmate_says(message: str):
    text = Text()
    text.append("OpsMate> ", style="bold green")
    text.append(message)
    console.print(text)


if __name__ == "__main__":
    opsmate_cli()
