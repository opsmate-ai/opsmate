from opsmate.dino.react import react
import asyncio

from opsmate.plugins import PluginRegistry

PluginRegistry.discover()


@react(
    model="gpt-4o",
    contexts=["you are a world class expert in answering questions"],
    tools=PluginRegistry.get_tools_from_list(["HttpToText", "ShellCommand"]),
    iterable=True,
)
async def answer(question: str):
    """
    You are a world class expert in answering questions.
    """
    return question


async def main():
    async for result in await answer(
        "summarise the top 10 news on https://news.ycombinator.com/"
    ):
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
