import pytest
from typing import Literal, Any
from opsmate.dino import run_react, dtool, dino
from opsmate.dino.react import react
from opsmate.dino.context import context
from opsmate.dino.types import React, ReactAnswer, Observation, ToolCall, Message


MODELS = ["gpt-4o", "claude-3-5-sonnet-20241022"]


class CalcResult(ToolCall):
    result: int


@dino("gpt-4o", response_model=int)
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
    async def use_calculator():
        return "don't do caculation yourself only use the calculator"

    @react(
        model="gpt-4o",
        contexts=[use_calculator],
        iterable=False,
        callback=lambda x: print(x),
    )
    async def calc_agent(query: str):
        return f"answer the query: {query}"

    answer = await calc_agent("what is (1 + 1) * 2?")
    assert await get_answer(answer.answer) == 4


@pytest.mark.asyncio
async def test_react_decorator_with_extra_contexts():
    @context(
        name="calc",
        tools=[calc],
    )
    async def use_calculator():
        return "don't do caculation yourself only use the calculator"

    @react(
        model="gpt-4o",
        iterable=False,
        callback=lambda x: print(x),
    )
    async def calc_agent(query: str):
        return f"answer the query: {query}"

    answer = await calc_agent("what is (1 + 1) * 2?", extra_contexts=[use_calculator])
    assert await get_answer(answer.answer) == 4


@pytest.mark.asyncio
async def test_react_decorator_with_extra_tools():
    @context(name="calc")
    async def use_calculator():
        return "don't do caculation yourself only use the calculator"

    @react(
        model="gpt-4o",
        tools=[calc],
        contexts=[use_calculator],
        iterable=False,
        callback=lambda x: print(x),
    )
    async def calc_agent(query: str):
        return f"answer the query: {query}"

    answer = await calc_agent("what is (1 + 1) * 2?", extra_tools=[calc])
    assert await get_answer(answer.answer) == 4


@pytest.mark.asyncio
async def test_react_decorator_with_custom_model():

    @react(
        model="gpt-4o",
        iterable=False,
        callback=lambda x: print(x),
    )
    async def what_is_the_llm():
        return "what is your name? \
            answer should be either OpenAI or Anthropic."

    @dino("gpt-4o-mini", response_model=Literal["OpenAI", "Anthropic"])
    async def category_llm(text: str):
        """
        return the name of the llm
        """
        return text

    answer = await category_llm(await what_is_the_llm())
    assert answer == "OpenAI"

    answer = await category_llm(
        await what_is_the_llm(model="claude-3-5-sonnet-20241022")
    )
    assert answer == "Anthropic"


@pytest.mark.asyncio
async def test_react_decorator_with_tool_call_context():
    @dtool
    async def weather(city: str, context: dict[str, Any] = {}) -> str:
        """
        return the weather of the city
        """
        return context[city]

    @react(
        model="gpt-4o",
        iterable=False,
        callback=lambda x: print(x),
        tools=[weather],
    )
    async def weather_agent(query: str):
        """
        You are a weather agent who has access to the real time weather through the `weather` tool.
        use the `weather` tool to get the weather of the city
        """
        return f"answer the query: {query} answer should be either sunny or cloudy"

    tool_call_context = {
        "Singapore": "sunny",
        "London": "cloudy",
    }
    answer = await weather_agent(
        "what is the weather in singapore?",
        tool_call_context=tool_call_context,
    )

    @dino("gpt-4o-mini", response_model=Literal["sunny", "cloudy"])
    def category_weather(weather: str):
        """
        categorize the weather into sunny or cloudy
        """
        return weather

    answer = await category_weather(answer.answer)
    assert answer == "sunny"

    answer = await weather_agent(
        "what is the weather in London?",
        tool_call_context=tool_call_context,
    )
    answer = await category_weather(answer.answer)
    assert answer == "cloudy"
