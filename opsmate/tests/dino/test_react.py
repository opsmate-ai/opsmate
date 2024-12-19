import pytest
from typing import Literal
from pydantic import BaseModel
from opsmate.dino import run_react, dtool, dino
from opsmate.dino.types import React, ReactAnswer, Observation


@pytest.mark.asyncio
async def test_run_react():
    class CalcResult(BaseModel):
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

    @dino("gpt-4o-mini", response_model=int)
    async def get_answer(text: str) -> str:
        """
        extract the answer from the text
        """
        return answer

    assert await get_answer(answer) == 4
