import pytest
from pydantic import BaseModel
from opsmate.dino import dino, dtool
from typing import Literal, Iterable


@pytest.mark.asyncio
async def test_dino_simple_extraction():
    class UserInfo(BaseModel):
        name: str
        email: str

    @dino("gpt-4o-mini", response_model=UserInfo)
    async def get_user_info(text: str):
        return f"extract the user info: {text}"

    user_info = await get_user_info(
        "My name is John Doe and my email is john.doe@example.com"
    )
    assert user_info.name == "John Doe"
    assert user_info.email == "john.doe@example.com"


async def test_doc_string_as_prompt():
    class UserInfo(BaseModel):
        name: str
        email: str

    @dino("gpt-4o-mini", response_model=UserInfo)
    async def get_user_info(text: str):
        """
        extract the user info. remember to sanitize the email address.
        e.g. john@hey.com -> [REDACTED]
        """
        return f"{text}"

    user_info = await get_user_info(
        "My name is John Doe and my email is john.doe@example.com"
    )
    assert user_info.name == "John Doe"
    assert user_info.email == "[REDACTED]"


async def test_dino_with_sync_tools():
    @dtool
    def get_weather(location: str) -> str:
        return f"The weather in {location} is sunny"

    @dino("gpt-4o-mini", tools=[get_weather], response_model=Literal["sunny", "cloudy"])
    async def get_weather_info(location: str):
        return f"What is the weather in {location}?"

    weather_info = await get_weather_info("San Francisco")
    assert weather_info == "sunny"


async def test_dino_with_async_tools():
    @dtool
    async def get_weather(location: str) -> str:
        return f"The weather in {location} is sunny"

    @dino("gpt-4o-mini", tools=[get_weather], response_model=Literal["sunny", "cloudy"])
    async def get_weather_info(location: str):
        return f"What is the weather in {location}?"

    weather_info = await get_weather_info("San Francisco")
    assert weather_info == "sunny"


async def test_dino_with_tool_outputs():
    @dtool
    def get_weather(location: str) -> str:
        return f"The weather in {location} is sunny"

    class WeatherInfo(BaseModel):
        weather: Literal["sunny", "cloudy"]
        tool_outputs: list[str]

    @dino("gpt-4o-mini", tools=[get_weather], response_model=WeatherInfo)
    async def get_weather_info(location: str):
        return f"What is the weather in {location}?"

    weather_info = await get_weather_info("San Francisco")
    assert weather_info.weather == "sunny"
    assert len(weather_info.tool_outputs) == 1
    assert (
        weather_info.tool_outputs[0].output == "The weather in San Francisco is sunny"
    )


async def test_dino_with_generator_response():
    class WeatherLookUp(BaseModel):
        """
        lookup the weather for the given location
        """

        location: str

    @dino("gpt-4o-mini", response_model=Iterable[WeatherLookUp])
    async def get_weather_info():
        return f"What's the weather like in San Francisco, London and Paris?"

    weather_info = await get_weather_info()
    assert len(weather_info) == 3
    locations = [info.location for info in weather_info]
    assert "San Francisco" in locations
    assert "London" in locations
    assert "Paris" in locations
