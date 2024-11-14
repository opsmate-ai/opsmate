from opsmate.libs.core.types import (
    Task,
    Metadata,
    TaskSpec,
    ReactOutput,
    ReactProcess,
    ReactAnswer,
    ExecResults,
    Context,
    ExecOutput,
    Agent,
)
from typing import List
from openai import OpenAI
from opsmate.libs.core.engine import exec_task
from opsmate.libs.core.engine.agent_executor import AgentExecutor, AgentCommand
from opsmate.libs.core.contexts import ExecShell
from opsmate.libs.contexts import available_contexts
from opsmate.libs.agents import available_agents, supervisor_agent
from opsmate.libs.opsmatefile import load_opsmatefile
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
import structlog
import logging
import queue
import threading
import time

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
@click.option(
    "--answer-only",
    is_flag=True,
    help="Only show the answer and not the thought, action and observation",
)
@click.option(
    "--contexts",
    default="cli",
    help="Comma separated list of contexts to use. To list all contexts please run the list-contexts command.",
)
@traceit
def run(instruction, ask, model, max_depth, answer_only, contexts):
    """
    Run a task with the OpsMate.
    """
    selected_contexts = get_contexts(contexts, with_react=False)

    task = Task(
        metadata=Metadata(
            name="run",
        ),
        spec=TaskSpec(
            input={},
            contexts=selected_contexts,
            instruction=instruction,
            response_model=ExecResults,
        ),
    )

    output = exec_task(OpenAI(), task, ask=ask, model=model)
    table = Table(title="Command Execution", show_header=True, show_lines=True)
    table.add_column("Command", style="cyan")
    table.add_column("Stdout", style="green")
    table.add_column("Stderr", style="red")
    table.add_column("Exit Code", style="magenta")
    for call in output.results:
        table.add_row(
            call.command,
            call.output.stdout,
            call.output.stderr,
            str(call.output.exit_code),
        )
    console.print(table)


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


@opsmate_cli.command()
@traceit
def list_contexts():
    """
    List all the contexts available in OpsMate.
    """

    table = Table(show_header=True, show_lines=True)
    table.add_column("Name")
    table.add_column("Description")
    for ctx in available_contexts:
        table.add_row(ctx.metadata.name, ctx.metadata.description)
    console.print(table)


@opsmate_cli.command()
@traceit
def list_agents():
    """
    List all the agents available in OpsMate.
    """
    table = Table(show_header=True, show_lines=True)
    table.add_column("Name")
    table.add_column("Description")

    # XXX: realise the agents, it's a bit hacky now
    agents = [fn() for fn in available_agents.values()]
    for agent in agents:
        table.add_row(agent.metadata.name, agent.metadata.description)
    console.print(table)


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
# @click.option(
#     "--answer-only",
#     is_flag=True,
#     help="Only show the answer and not the thought, action and observation",
# )
@click.option(
    "--stream",
    is_flag=True,
    help="Stream the output of the commands",
)
@click.option(
    "--agents",
    default="cli-agent",
    help="Comma separated list of agents to use. To list all agents please run the list-agents command.",
)
@click.option(
    "--skip-opsmatefile",
    is_flag=True,
    help="Skip loading OpsMatefile",
)
@traceit
def chat(ask, model, max_depth, agents, skip_opsmatefile, stream):
    executor = AgentExecutor(OpenAI())
    # check if Opsmatefile exists in the cwd
    if skip_opsmatefile or not os.path.exists("Opsmatefile"):
        if skip_opsmatefile:
            console.print("OpsMatefile is skipped", style="yellow")
        else:
            console.print("OpsMatefile not found", style="red")

        selected_agents = get_agents(
            agents, react_mode=True, max_depth=max_depth, model=model
        )

        supervisor = supervisor_agent(
            extra_contexts="You are a helpful SRE manager who manages a team of SMEs",
            agents=selected_agents,
        )
    else:
        console.print("OpsMatefile detected, loading supervisor", style="green")
        console.print(
            "--model, --max-depth and --agents options are ignored when using OpsMatefile",
            style="yellow",
        )
        world = load_opsmatefile("Opsmatefile")
        supervisor = world.supervisor_agent()

        console.print("Ingesting documents", style="green")
        world.ingest_documents()
        console.print("Documents ingested", style="green")

    try:
        opsmate_says("Howdy! How can I help you?\n" + help_msg)

        while True:
            # user_input = click.prompt("You")
            user_input = console.input("[bold cyan]You> [/bold cyan]")
            if user_input == "!clear":
                executor.clear_history(supervisor)
                opsmate_says("Chat history cleared")
                continue
            elif user_input == "!exit":
                break
            elif user_input == "!help":
                console.print(help_msg)
                continue

            run_supervisor(
                executor,
                supervisor,
                user_input,
                stream=stream,
                stream_output=queue.Queue(),
            )
    except (KeyboardInterrupt, EOFError):
        opsmate_says("Goodbye!")


@traceit(name="run_supervisor", exclude=["stream_output"])
def run_supervisor(
    executor: AgentExecutor,
    supervisor: Agent,
    instruction: str,
    stream: bool = False,
    stream_output: queue.Queue = None,
):
    execution = executor.supervise(
        supervisor, instruction, stream=stream, stream_output=stream_output
    )

    # stream the command outputs
    def stream_output_handler():
        while True:
            try:
                output = stream_output.get(block=False)
                if isinstance(output, ExecOutput):
                    if output.exit_code == -1:
                        if output.stdout != "":
                            print(output.stdout)
                        if output.stderr != "":
                            print(output.stderr)
                elif isinstance(output, ExecShell):
                    print(f"ExecShell: {output.command}")
            except queue.Empty:
                time.sleep(0.001)
                pass

    thread = threading.Thread(
        target=stream_output_handler,
        daemon=True,  # Consider setting this to True if needed
    )

    thread.start()

    for step in execution:
        actor, output = step
        if actor == "@supervisor":
            if isinstance(output, ReactProcess):
                table = Table(
                    title="@supervisor Thought Process",
                    show_header=False,
                    show_lines=True,
                )
                table.add_row("Thought", output.thought)
                table.add_row("Action", output.action)
                console.print(table)
            elif isinstance(output, ReactAnswer):
                table = Table(
                    title="@supervisor Answer", show_header=False, show_lines=True
                )
                table.add_row("Answer", output.answer)
                console.print(table)
        else:
            if isinstance(output, ExecResults):
                for result in output.results:
                    table = Table(
                        title=result.table_title(), show_header=True, show_lines=True
                    )
                    table.add_column("Agent", style="cyan")
                    for column in result.table_column_names():
                        table.add_column(column[0], style=column[1])

                    table.add_row(
                        actor,
                        *result.table_columns(),
                    )
                    console.print(table)
            elif isinstance(output, AgentCommand):
                table = Table(title="Agent Command", show_header=False, show_lines=True)
                table.add_row("Agent", output.agent)
                table.add_row("Command", output.instruction)
                console.print(table)
            elif isinstance(output, ReactAnswer):
                table = Table(
                    title=f"{actor} Answer", show_header=False, show_lines=True
                )
                table.add_row("Answer", output.answer)
                console.print(table)
            elif isinstance(output, ReactProcess):
                table = Table(
                    title=f"{actor} Throught Process",
                    show_header=False,
                    show_lines=True,
                )
                table.add_row("Thought", output.thought)
                table.add_row("Action", output.action)
                console.print(table)


def opsmate_says(message: str):
    text = Text()
    text.append("OpsMate> ", style="bold green")
    text.append(message)
    console.print(text)


def get_contexts(contexts: str, with_react: bool = True):
    context_list = contexts.split(",")
    if with_react:
        context_list.append("react")
    context_list = list(set(context_list))

    selected_contexts = []
    for ctx_name in context_list:
        for ctx in available_contexts:
            if ctx.metadata.name == ctx_name:
                selected_contexts.append(ctx)
                break
        else:
            console.print(f"Context {ctx_name} not found", style="red")
            exit(1)

    return selected_contexts


def get_agents(
    agents: str, react_mode: bool = False, max_depth: int = 10, model: str = "gpt-4o"
):
    agent_list = agents.split(",")

    if agent_list == ["all"]:
        agent_list = list(available_agents.keys())

    selected_agent_fns = []
    for agent_name in agent_list:
        if agent_name in available_agents:
            selected_agent_fns.append(available_agents[agent_name])
        else:
            console.print(f"Agent {agent_name} not found", style="red")
            exit(1)

    agents: List[Agent] = [
        fn(react_mode=react_mode, max_depth=max_depth, model=model)
        for fn in selected_agent_fns
    ]

    return agents


if __name__ == "__main__":
    opsmate_cli()
