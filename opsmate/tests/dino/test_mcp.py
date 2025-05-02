from opsmate.dino.mcp import Server
from opsmate.dino import dino
import pytest


@pytest.mark.asyncio
async def test_server():
    server = Server(
        name="time",
        config={"command": "docker", "args": ["run", "-i", "--rm", "mcp/time"]},
    )
    await server.initialize()

    tools = await server.list_tools()

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
    print(result)
