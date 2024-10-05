from opsmate.libs.core.engine.agent_executor import AgentExecutor, supervisor_agent
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
    agent = Agent(
        metadata=Metadata(
            name="CLI Agent",
            description="Agent to run CLI commands",
            apiVersion="v1",
        ),
        status=AgentStatus(),
        spec=AgentSpec(
            react_mode=False,
            model="gpt-4o",
            max_depth=10,
            description="Agent to run CLI commands",
            task_template=TaskTemplate(
                metadata=Metadata(
                    name="cli tool",
                    apiVersion="v1",
                    description="Run CLI command",
                ),
                spec=TaskSpecTemplate(
                    contexts=[cli_ctx],
                    response_model=BaseTaskOutput,
                ),
            ),
        ),
    )

    supervisor = supervisor_agent(agents=[agent])

    executor = AgentExecutor(Client())
    # execution = executor.execute(
    #     agent,
    #     "what's the current ip location? use cli to find out",
    # )
    # for step in execution:
    #     print(step)

    execution = executor.supervise(
        supervisor, "what's the cpu ram and disk space of the current machine?"
    )
    for step in execution:
        print(step)


if __name__ == "__main__":
    main()
