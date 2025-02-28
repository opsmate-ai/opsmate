import pytest
from opsmate.dino import dino, dtool, run_react
from opsmate.contexts.k8s import k8s_ctx
from opsmate.dino.types import ReactAnswer
from typing import Annotated
import structlog

logger = structlog.get_logger(__name__)


@dtool
async def k8s_agent(
    problem: Annotated[str, "High level problem to solve"],
    question: Annotated[str, "The question to solve"],
) -> str:
    """
    k8s_agent is a tool that solves a problem using kubectl.
    """
    logger.info("solving query", problem=problem, question=question)

    async for result in run_react(
        question,
        context=k8s_ctx.resolve_contexts(),
        tools=k8s_ctx.resolve_tools(),
    ):
        logger.info(result)

        if isinstance(result, ReactAnswer):
            return result.answer


@dino("gpt-4o", response_model=str, tools=[k8s_agent])
async def sre_manager(query: str):
    """
    You are a world class SRE manager who manages a team of SREs.
    """
    return f"answer the query: {query}"


@dino("gpt-4o-mini", response_model=int)
async def extract_number(text: str):
    return f"extract the number from {text}"


# @pytest.mark.asyncio
# async def test_k8s_agent():
#     result = await sre_manager("how many pods are running in the cluster?")
#     assert await extract_number(result) == 18
