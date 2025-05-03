from pydantic import BaseModel, Field, create_model
from typing import Any, Type
from mcp import ClientSession, StdioServerParameters
from mcp.types import CallToolResult
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
from opsmate.dino.types import ToolCall, register_tool
from opsmate.dino.utils import json_schema_to_pydantic_model
import asyncio
import structlog
import os

logger = structlog.get_logger(__name__)


class MCPConfig(BaseModel):
    command: str
    args: list[str] = Field(default=[])
    env: dict[str, str] = Field(default={})


# From https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/clients/simple-chatbot/mcp_simple_chatbot/main.py
class Server:
    """Manages MCP server connections and tool execution."""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name: str = name
        self.config: dict[str, Any] = config
        self.stdio_context: Any | None = None
        self.session: ClientSession | None = None
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.exit_stack: AsyncExitStack = AsyncExitStack()

    async def initialize(self) -> None:
        """Initialize the server connection."""
        command = self.config["command"]
        if command is None:
            raise ValueError("The command must be a valid string and cannot be None.")

        server_params = StdioServerParameters(
            command=command,
            args=self.config["args"],
            env=(
                {**os.environ, **self.config["env"]} if self.config.get("env") else None
            ),
            cwd=self.config.get("cwd", None),
        )
        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.session = session
        except Exception as e:
            logger.error("Error initializing server", error=e, server_name=self.name)
            await self.cleanup()
            raise

    async def list_tools(self) -> list[Any]:
        """List available tools from the server.

        Returns:
            A list of available tools.

        Raises:
            RuntimeError: If the server is not initialized.
        """
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        tools_response = await self.session.list_tools()
        tools = []

        for item in tools_response:
            if isinstance(item, tuple) and item[0] == "tools":
                tools.extend(
                    mcp_to_dino_tool(
                        self.session,
                        self.name,
                        tool.name,
                        tool.description,
                        tool.inputSchema,
                    )
                    for tool in item[1]
                )

        return tools

    async def cleanup(self) -> None:
        """Clean up server resources."""
        async with self._cleanup_lock:
            try:
                await self.exit_stack.aclose()
                self.session = None
                self.stdio_context = None
            except Exception as e:
                logger.error("Error during cleanup", error=e, server_name=self.name)


def snake_to_pascal(snake_str: str) -> str:
    """Convert snake_case string to PascalCase."""
    components = snake_str.split("_")
    return "".join(x.title() for x in components)


def mcp_to_dino_tool(
    session: ClientSession,
    server_name: str,
    tool_name: str,
    tool_description: str,
    tool_input_schema: dict[str, Any],
) -> Type[ToolCall[CallToolResult]]:
    """Convert an MCP tool specification into a dino.ToolCall subclass type.

    Args:
        session: The MCP session to use for tool execution.
        server_name: The name of the MCP server (e.g., "mcp/time").
        tool_name: The name of the MCP tool (e.g., "run_terminal_cmd").
        tool_description: The description of the tool.
        tool_input_schema: The JSON schema dictionary defining the tool's input arguments.

    Returns:
        A dynamically created class (type) that inherits from ToolCall[Any]
        and a Pydantic model generated from the input_schema.
    """
    class_name = snake_to_pascal(tool_name)

    # Generate the Pydantic model from the JSON schema for input arguments
    InputModel = json_schema_to_pydantic_model(tool_input_schema, class_name + "Input")

    async def call(self, context: dict[str, Any] = {}) -> CallToolResult:
        return await session.call_tool(tool_name, self.model_dump())

    def markdown(self, context: dict[str, Any] = {}) -> str:
        return f"""
### MCP Tool Execution: {class_name}

### Output

```json
{self.model_dump_json()}
```
"""

    # Dynamically create the ToolCall subclass using create_model
    DinoToolClass = create_model(
        class_name,
        __base__=(ToolCall[CallToolResult], InputModel),
        __doc__=tool_description,
        _mcp_tool_name=f"{server_name}/{tool_name}",
        __call__=call,
        markdown=markdown,
    )

    # Ensure the created class is recognized as a subclass of ToolCall
    assert issubclass(DinoToolClass, ToolCall)

    return register_tool()(DinoToolClass)
