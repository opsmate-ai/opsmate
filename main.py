from opsmate.dino import dino
from opsmate.tools import KnowledgeRetrieval, ShellCommand
from opsmate.ingestions import ingest_from_config
from opsmate.libs.config import Config
import asyncio


@dino(
    model="gpt-4o",
    response_model=str,
    tools=[
        KnowledgeRetrieval,
        ShellCommand,
    ],
)
async def answer(question: str):
    """
    You are a world class expert in answering questions.
    Do not use command tools for knowledge retrieval.
    """
    return question


async def main():
    cfg = Config()
    await ingest_from_config(cfg)

    result = await answer("what is the health check endpoint for the payment service?")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
