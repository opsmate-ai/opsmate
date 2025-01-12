from opsmate.plugins import auto_discover
from opsmate.dino import dino, dtool
from typing import Literal


@auto_discover(
    author="opsmate",
    version="0.1.0",
)
@dino(model="gpt-4o-mini", response_model=Literal["anthropic", "openai"])
async def my_creator():
    """you are a LLM"""
    return "your creator"


@dtool
def get_weather(location: str) -> str:
    return f"The location is {location}. if it's London return raining other wise return sunny"


@auto_discover(
    name="fake_weather",
    description="get the weather",
    author="opsmate",
    version="0.1.0",
)
@dino(
    model="gpt-4o-mini", response_model=Literal["sunny", "rainy"], tools=[get_weather]
)
async def weather(location: str):
    """the the current weather"""
    return f"check the weather for {location}"


@auto_discover(
    name="fake_weather_sync",
    description="the the current weather",
    author="opsmate",
    version="0.1.0",
)
@dino(
    model="gpt-4o-mini", response_model=Literal["sunny", "rainy"], tools=[get_weather]
)
# same function name is supported as long as it's auto-discovered with a different name
def weather(location: str) -> str:
    """the the current weather"""
    return f"check the weather for {location}"
