from opsmate.dino.mcp import Server
from opsmate.dino import dino
import pytest
import os


@pytest.mark.asyncio
async def test_server():
    cwd = os.path.dirname(os.path.abspath(__file__))
    mcp_path = os.path.join(cwd, "fixtures", "mcp")
    server = Server(
        name="time",
        config={
            "command": "python",
            "args": [
                os.path.join(mcp_path, "servers.py"),
            ],
            "cwd": mcp_path,
        },
    )
    await server.initialize()

    tools = await server.list_tools()
    assert len(tools) == 1
    tool = tools[0]
    assert tool._mcp_tool_name.default == "time/get_current_time"
    assert tool.__doc__ == "Get the current time in a specific timezone"

    @dino(
        model="gpt-4o-mini",
        response_model=str,
        tools=tools,
    )
    async def time_agent(query: str):
        """
        You have access to the time tools, answer any question about the time.
        """
        return query

    result = await time_agent("What is the time in London?")
    assert (
        isinstance(result, str) and result
    ), "time_agent should return a non-empty string"
