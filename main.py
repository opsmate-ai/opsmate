from opsmate.libs.core.engine.agent_executor import AgentExecutor
from opsmate.libs.core.agents import (
    supervisor_agent,
    cli_agent,
    k8s_agent,
    AgentCommand,
)
from opsmate.libs.core.types import ReactProcess, ReactAnswer, ExecResult
from openai import Client
import structlog
import logging
import os
from rich.console import Console
from rich.table import Table
from rich.text import Text
import sys

console = Console()

loglevel = os.getenv("LOGLEVEL", "ERROR").upper()
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelNamesMapping()[loglevel]
    ),
)


def main(instruction: str):
    supervisor = supervisor_agent(
        extra_context="You are a helpful SRE manager who manages a team of SMEs",
        agents=[
            cli_agent(react_mode=True),
            k8s_agent(react_mode=True),
        ],
    )

    executor = AgentExecutor(Client())

    execution = executor.supervise(supervisor, instruction)
    for step in execution:
        actor, output = step
        if actor == "@supervisor":
            if isinstance(output, ReactProcess):
                table = Table(
                    title="@supervisor Thought Process",
                    show_header=False,
                    show_lines=True,
                )
                table.add_row("Question", output.question)
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
            if isinstance(output, ExecResult):
                table = Table(
                    title="Command Execution", show_header=True, show_lines=True
                )
                table.add_column("Agent", style="cyan")
                table.add_column("Command", style="cyan")
                table.add_column("Stdout", style="green")
                table.add_column("Stderr", style="red")
                table.add_column("Exit Code", style="magenta")
                for call in output.calls:
                    table.add_row(
                        actor,
                        call.command,
                        call.output.stdout,
                        call.output.stderr,
                        str(call.output.exit_code),
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
                table.add_row("Question", output.question)
                table.add_row("Thought", output.thought)
                table.add_row("Action", output.action)
                console.print(table)


if __name__ == "__main__":
    main(sys.argv[1])
