from opsmate.libs.core.engine.agent_executor import AgentExecutor
from opsmate.libs.core.agents import supervisor_agent, cli_agent, k8s_agent
from opsmate.libs.core.types import (
    Agent,
    AgentSpec,
    AgentStatus,
    Metadata,
    TaskTemplate,
    TaskSpecTemplate,
    ReactOutput,
    BaseTaskOutput,
)
from opsmate.libs.contexts import cli_ctx, react_ctx
from openai import Client
import structlog
import logging
import os

loglevel = os.getenv("LOGLEVEL", "ERROR").upper()
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelNamesMapping()[loglevel]
    ),
)


def main():
    supervisor = supervisor_agent(
        extra_context="You are a helpful SRE manager who manages a sysadmin and a k8s SME",
        agents=[
            cli_agent(),
            k8s_agent(),
        ],
    )

    executor = AgentExecutor(Client())
    # execution = executor.execute(
    #     agent,
    #     "what's the current ip location? use cli to find out",
    # )
    # for step in execution:
    #     print(step)

    execution = executor.supervise(
        supervisor, "what's the current k8s cluster context?"
    )
    for step in execution:
        print(step)


if __name__ == "__main__":
    main()
