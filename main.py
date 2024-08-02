from libs.core.types import *


os_ctx = Context(
    metadata=Metadata(
        name="os",
        apiVersion="v1",
        labels={"type": "system"},
        description="System tools",
    ),
    spec=ContextSpec(tools=[], instruction="find what's the current os"),
)

os_cli_tool = Tool(
    metadata=Metadata(
        name="cli", apiVersion="v1", labels={"type": "system"}, description="System CLI"
    ),
    spec=ToolSpec(
        params={},
        contexts=[os_ctx],
        instruction="you are a sysadmin specialised in OS commands",
    ),
)

task = Task(
    metadata=Metadata(
        name="list the files in the current directory",
        apiVersion="v1",
    ),
    spec=TaskSpec(
        input={},
        contexts=[],
        tools=[os_cli_tool],
        instruction="list the files in the current directory",
        response_model=str,
    ),
)
