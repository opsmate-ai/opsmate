import pytest
from typing import Literal
from opsmate.dino import run_react, dtool, dino
from opsmate.dino.types import React, ReactAnswer, Observation, ToolCall


MODELS = ["gpt-4o-mini", "claude-3-5-sonnet-20241022"]


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS)
async def test_run_react(model: str):
    class CalcResult(ToolCall):
        result: int

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

    answer = None
    async for result in run_react(
        question="what is (1 + 1) * 2?",
        pretext="don't do caculation yourself only use the calculator",
        tools=[calc],
    ):
        assert isinstance(result, (React, ReactAnswer, Observation))

        if isinstance(result, ReactAnswer):
            answer = result.answer
            break

    assert answer is not None

    @dino(model, response_model=int)
    async def get_answer(text: str) -> str:
        """
        extract the answer from the text
        """
        return answer

    assert await get_answer(answer) == 4
