import pytest
from typing import Literal
from opsmate.dino import run_react, dtool, dino
from opsmate.dino.react import react
from opsmate.dino.context import context
from opsmate.dino.types import React, ReactAnswer, Observation, ToolCall, Message


MODELS = ["gpt-4o-mini", "claude-3-5-sonnet-20241022"]


class CalcResult(ToolCall):
    result: int


@dino("gpt-4o-mini", response_model=int)
async def get_answer(answer: str):
    """
    extract the answer from the text
    """
    return answer


@dtool
def calc(a: int, b: int, op: Literal["add", "sub", "mul", "div"]) -> CalcResult:
    if op == "add":
        return CalcResult(result=a + b)
    elif op == "sub":
        return CalcResult(result=a - b)
    elif op == "mul":
        return CalcResult(result=a * b)
    elif op == "div":
        return CalcResult(result=a / b)


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS)
async def test_run_react(model: str):

    answer = None
    async for result in run_react(
        question="what is (1 + 1) * 2?",
        contexts=["don't do caculation yourself only use the calculator"],
        tools=[calc],
    ):
        assert isinstance(result, (React, ReactAnswer, Observation))

        if isinstance(result, ReactAnswer):
            answer = result.answer
            break

    assert answer is not None

    assert await get_answer(answer) == 4


@pytest.mark.asyncio
async def test_run_react_with_messages_as_contexts():
    answer = None
    async for result in run_react(
        question="what is (1 + 1) * 2?",
        contexts=[
            Message.system("don't do caculation yourself only use the calculator")
        ],
        tools=[calc],
    ):
        assert isinstance(result, (React, ReactAnswer, Observation))

        if isinstance(result, ReactAnswer):
            answer = result.answer
            break

    assert answer is not None

    assert await get_answer(answer) == 4


@pytest.mark.asyncio
async def test_react_decorator():
    @react(
        model="gpt-4o",
        tools=[calc],
        contexts=["don't do caculation yourself only use the calculator"],
    )
    async def calc_agent(query: str):
        return f"answer the query: {query}"

    answer = await calc_agent("what is (1 + 1) * 2?")

    assert await get_answer(answer.answer) == 4


@pytest.mark.asyncio
async def test_react_decorator_callback():
    outs = []

    async def callback(result: React | ReactAnswer | Observation):
        outs.append(result)

    @react(
        model="gpt-4o",
        tools=[calc],
        contexts=["don't do caculation yourself only use the calculator"],
        callback=callback,
    )
    async def calc_agent(query: str):
        return f"answer the query: {query}"

    answer = await calc_agent("what is (1 + 1) * 2?")
    assert await get_answer(answer.answer) == 4

    assert len(outs) > 0
    for out in outs:
        assert isinstance(out, (React, ReactAnswer, Observation))


@pytest.mark.asyncio
async def test_react_decorator_iterable():
    @react(
        model="gpt-4o",
        tools=[calc],
        contexts=["don't do caculation yourself only use the calculator"],
        iterable=True,
    )
    async def calc_agent(query: str):
        return f"answer the query: {query}"

    async for result in await calc_agent("what is (1 + 1) * 2?"):
        print(result)
        assert isinstance(result, (React, ReactAnswer, Observation))


@pytest.mark.asyncio
async def test_react_decorator_with_contexts():
    @context(
        name="calc",
        tools=[calc],
    )
    def use_calculator():
        return "don't do caculation yourself only use the calculator"

    @react(
        model="gpt-4o",
        contexts=[use_calculator()],
        iterable=False,
        callback=lambda x: print(x),
    )
    async def calc_agent(query: str):
        return f"answer the query: {query}"

    answer = await calc_agent("what is (1 + 1) * 2?")
    assert await get_answer(answer.answer) == 4
