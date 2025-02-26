from opsmate.libs.core.trace import traceit
from openai_otel import OpenAIAutoInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt
from rich.markdown import Markdown
from opsmate.dino import dino, run_react
from opsmate.dino.types import Observation, ReactAnswer, React, Message
from opsmate.tools.command_line import ShellCommand
from opsmate.dino.provider import Provider
from opsmate.contexts import contexts
from functools import wraps
from opsmate.libs.config import config
from opsmate.plugins import PluginRegistry
import asyncio
import os
import click
import structlog
import sys

PluginRegistry.discover(config.plugins_dir)


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


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


class StdinArgument(click.ParamType):
    name = "stdin"

    def convert(self, value, param, ctx):
        if value == "-":
            return sys.stdin.read().strip()
        return value


@click.group()
def opsmate_cli():
    """
    OpsMate is an SRE AI assistant that helps you manage production environment.
    This is the cli tool to interact with OpsMate.
    """
    pass


def common_params(func):
    @click.option(
        "--tools",
        default="",
        help="Comma separated list of tools to use",
    )
    @click.option(
        "-r",
        "--review",
        is_flag=True,
        default=False,
        show_default=True,
        help="Review and edit commands before execution",
    )
    @click.option(
        "-s",
        "--system-prompt",
        default=None,
        show_default=True,
        help="System prompt to use",
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
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

        review = kwargs.pop("review", False)
        kwargs["tool_call_context"] = {}
        if review:
            kwargs["tool_call_context"]["confirmation"] = confirmation_prompt

        return func(*args, **kwargs)

    return wrapper


async def confirmation_prompt(tool_call: ShellCommand):
    console.print(
        Markdown(
            f"""
## Command Confirmation

Edit the command if needed, then press Enter to execute:
!cancel - Cancel the command
"""
        )
    )
    try:
        prompt = Prompt.ask(
            "Press Enter or edit the command",
            default=tool_call.command,
        )
        tool_call.command = prompt
        if prompt == "!cancel":
            return False
        return True
    except (KeyboardInterrupt, EOFError):
        console.print("\nCommand cancelled")
        return False


@opsmate_cli.command()
@click.argument("instruction", type=StdinArgument())
@click.option(
    "-m",
    "--model",
    show_default=True,
    default="gpt-4o",
    help="OpenAI model to use. To list models available please run the list-models command.",
)
@click.option(
    "-c",
    "--context",
    show_default=True,
    default="cli",
    help="Context to be added to the prompt. Run the list-contexts command to see all the contexts available.",
)
@click.option(
    "-n",
    "--no-tool-output",
    is_flag=True,
    help="Do not print tool outputs",
)
@common_params
@traceit
@coro
async def run(
    instruction, model, context, tools, tool_call_context, system_prompt, no_tool_output
):
    """
    Run a task with the OpsMate.
    """

    ctx = get_context(context)

    if len(tools) == 0:
        tools = ctx.tools

    logger.info("Running on", instruction=instruction, model=model)

    @dino("gpt-4o", response_model=Observation, tools=tools)
    async def run_command(instruction: str, context={}):
        return [
            (
                Message.system(f"<system_prompt>{system_prompt}</system_prompt>")
                if system_prompt
                else Message.system(ctx.ctx())
            ),
            Message.user(instruction),
        ]

    observation = await run_command(instruction, context=tool_call_context)

    if not no_tool_output:
        for tool_call in observation.tool_outputs:
            console.print(Markdown(tool_call.markdown()))
        console.print(Markdown(observation.observation))
    else:
        print(observation.observation)


@opsmate_cli.command()
@click.argument("instruction", type=StdinArgument())
@click.option(
    "-m",
    "--model",
    default="gpt-4o",
    show_default=True,
    help="OpenAI model to use. To list models available please run the list-models command.",
)
@click.option(
    "-i",
    "--max-iter",
    default=10,
    show_default=True,
    help="Max number of iterations the AI assistant can reason about",
)
@click.option(
    "-c",
    "--context",
    default="cli",
    show_default=True,
    help="Context to be added to the prompt. Run the list-contexts command to see all the contexts available.",
)
@click.option(
    "-n",
    "--no-tool-output",
    is_flag=True,
    help="Do not print tool outputs",
)
@click.option(
    "-a",
    "--answer-only",
    is_flag=True,
    help="Print only the answer",
)
@common_params
@traceit
@coro
async def solve(
    instruction,
    model,
    max_iter,
    context,
    tools,
    tool_call_context,
    system_prompt,
    no_tool_output,
    answer_only,
):
    """
    Solve a problem with the OpsMate.
    """
    ctx = get_context(context)

    if len(tools) == 0:
        tools = ctx.tools

    contexts = [
        Message.system(system_prompt) if system_prompt else Message.system(ctx.ctx())
    ]

    async for output in run_react(
        instruction,
        contexts=contexts,
        model=model,
        max_iter=max_iter,
        tools=tools,
        tool_call_context=tool_call_context,
    ):
        match output:
            case React():
                if answer_only:
                    continue
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
            case Observation():
                if answer_only:
                    continue
                console.print(Markdown("## Observation"))
                if not no_tool_output:
                    for tool_call in output.tool_outputs:
                        console.print(Markdown(tool_call.markdown()))
                console.print(Markdown(output.observation))
            case ReactAnswer():
                if answer_only:
                    print(output.answer)
                    break
                console.print(
                    Markdown(
                        f"""
## Answer

{output.answer}
"""
                    )
                )


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
async def chat(model, max_iter, context, tools, tool_call_context, system_prompt):
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

        contexts = [
            (
                Message.system(f"<system_prompt>{system_prompt}</system_prompt>")
                if system_prompt
                else Message.system(ctx.ctx())
            )
        ]
        run = run_react(
            user_input,
            contexts=contexts,
            model=model,
            max_iter=max_iter,
            tools=tools,
            chat_history=chat_history,
            tool_call_context=tool_call_context,
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
@click.option("--skip-confirm", is_flag=True, help="Skip confirmation")
@coro
async def reset(skip_confirm):
    """
    Reset the OpsMate.
    """
    from opsmate.libs.config import config
    import glob
    import shutil

    def remove_db_url(db_url):
        if db_url == ":memory:":
            return

        # Remove the main db and all related files (journal, wal, shm, etc)
        for f in glob.glob(f"{db_url}*"):
            if os.path.exists(f):
                if os.path.isdir(f):
                    shutil.rmtree(f, ignore_errors=True)
                else:
                    os.remove(f)

    def remove_embeddings_db_path(embeddings_db_path):
        shutil.rmtree(embeddings_db_path, ignore_errors=True)

    db_url = config.db_url
    db_url = db_url.replace("sqlite:///", "")

    if skip_confirm:
        console.print("Resetting OpsMate")
        remove_db_url(db_url)
        remove_embeddings_db_path(config.embeddings_db_path)
        return

    if (
        Prompt.ask(
            f"""Are you sure you want to reset OpsMate? This will delete:
- {db_url}
- {config.embeddings_db_path}
""",
            default="no",
            choices=["yes", "no"],
        )
        == "no"
    ):
        console.print("Reset cancelled")
        return

    remove_db_url(db_url)
    remove_embeddings_db_path(config.embeddings_db_path)


@opsmate_cli.command()
@click.option(
    "-h", "--host", default="0.0.0.0", show_default=True, help="Host to serve on"
)
@click.option("-p", "--port", default=8080, show_default=True, help="Port to serve on")
@click.option(
    "-w",
    "--workers",
    default=2,
    show_default=True,
    help="Number of uvicorn workers to serve on",
)
@coro
async def serve(host, port, workers):
    """
    Start the OpsMate server.
    """
    import uvicorn
    from opsmate.gui.app import on_startup, kb_ingest

    await on_startup()
    await kb_ingest()

    if workers > 1:
        uvicorn.run(
            "opsmate.apiserver.apiserver:app",
            host=host,
            port=port,
            workers=workers,
        )
    else:
        config = uvicorn.Config("opsmate.apiserver.apiserver:app", host=host, port=port)
        server = uvicorn.Server(config)
        await server.serve()


@opsmate_cli.command()
@click.option(
    "-w",
    "--workers",
    default=10,
    show_default=True,
    help="Number of concurrent background workers",
)
@coro
async def worker(workers):
    """
    Start the OpsMate worker.
    """
    from opsmate.dbqapp import app as dbqapp

    try:
        task = asyncio.create_task(dbqapp.main(workers))
        await task
    except KeyboardInterrupt:
        task.cancel()
        await task


@opsmate_cli.command()
def list_tools():
    """
    List all the tools available.
    """

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


@opsmate_cli.command()
@click.option(
    "--source",
    help="Source of the knowledge base fs:////path/to/kb or github:///owner/repo[:branch]",
)
@click.option(
    "--path",
    default="/",
    show_default=True,
    help="Path to the knowledge base",
)
@click.option(
    "--glob",
    default="**/*.md",
    show_default=True,
    help="Glob to use to find the knowledge base",
)
@coro
async def ingest(source, path, glob):
    """
    Ingest a knowledge base.
    Notes the ingestion worker needs to be started separately with `opsmate worker`.
    """

    from opsmate.libs.config import config
    from sqlmodel import create_engine, text, Session
    from opsmate.dbq.dbq import enqueue_task
    from opsmate.ingestions.jobs import ingest

    engine = create_engine(
        config.db_url,
        connect_args={"check_same_thread": False},
        # echo=True,
    )
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.close()

    splitted = source.split(":///")
    if len(splitted) != 2:
        console.print(
            "Invalid source. Use the format fs:///path/to/kb or github:///owner/repo[:branch]"
        )
        exit(1)

    provider, source = splitted

    if ":" in source:
        source, branch = source.split(":")
    else:
        branch = "main"

    splitter_config = config.splitter_config

    with Session(engine) as session:
        match provider:
            case "fs":
                enqueue_task(
                    session,
                    ingest,
                    ingestor_type="fs",
                    ingestor_config={"local_path": source, "glob_pattern": glob},
                    splitter_config=splitter_config,
                )
            case "github":
                enqueue_task(
                    session,
                    ingest,
                    ingestor_type="github",
                    ingestor_config={
                        "repo": source,
                        "branch": branch,
                        "path": path,
                        "glob": glob,
                    },
                    splitter_config=splitter_config,
                )
    console.print("Ingesting knowledges in the background...")


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
