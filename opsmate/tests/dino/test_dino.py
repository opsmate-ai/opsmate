import pytest
from pydantic import BaseModel, ValidationInfo, model_validator
from opsmate.dino import dino, dtool
from typing import Literal, Iterable, Any, List
from openai import AsyncOpenAI
import instructor
from opsmate.dino.types import ResponseWithToolOutputs, Message, ToolCall
import os

MODELS = ["gpt-4o-mini", "claude-3-5-sonnet-20241022"]

if os.getenv("XAI_API_KEY"):
    MODELS.append("grok-2-1212")


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS)
async def test_dino_simple_extraction(model: str):
    class UserInfo(BaseModel):
        name: str
        email: str

    @dino(model, response_model=UserInfo)
    async def get_llm_info(text: str):
        return f"extract the user info: {text}"

    user_info = await get_llm_info(
        "My name is John Doe and my email is john.doe@example.com"
    )
    assert user_info.name == "John Doe"
    assert user_info.email == "john.doe@example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS)
async def test_doc_string_as_prompt(model: str):
    class UserInfo(BaseModel):
        name: str
        email: str

    @dino(model, response_model=UserInfo)
    async def get_llm_info(text: str):
        """
        extract the user info. remember to sanitize the email address.
        e.g. john@hey.com -> [REDACTED]
        """
        return f"{text}"

    user_info = await get_llm_info(
        "My name is John Doe and my email is john.doe@example.com"
    )
    assert user_info.name == "John Doe"
    assert user_info.email == "[REDACTED]"


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS)
async def test_dino_with_sync_tools(model: str):
    @dtool
    def get_weather(location: str) -> str:
        return f"The weather in {location} is sunny"

    @dino(model, tools=[get_weather], response_model=Literal["sunny", "cloudy"])
    async def get_weather_info(location: str):
        return f"What is the weather in {location}?"

    weather_info = await get_weather_info("San Francisco")
    assert weather_info == "sunny"


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS)
async def test_dino_with_async_tools(model: str):
    @dtool
    async def get_weather(location: str) -> str:
        return f"The weather in {location} is sunny"

    @dino(model, tools=[get_weather], response_model=Literal["sunny", "cloudy"])
    async def get_weather_info(location: str):
        return f"What is the weather in {location}?"

    weather_info = await get_weather_info("San Francisco")
    assert weather_info == "sunny"


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS)
async def test_dino_with_tool_outputs(model: str):
    @dtool
    def get_weather(location: str) -> str:
        return f"The weather in {location} is sunny"

    class WeatherInfo(ResponseWithToolOutputs[str]):
        weather: Literal["sunny", "cloudy"]

    @dino(model, tools=[get_weather], response_model=WeatherInfo)
    async def get_weather_info(location: str):
        return f"What is the weather in {location}?"

    weather_info = await get_weather_info("San Francisco")
    assert weather_info.weather == "sunny"
    assert len(weather_info.tool_outputs) == 1
    assert (
        weather_info.tool_outputs[0].output == "The weather in San Francisco is sunny"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS)
async def test_dino_with_generator_response(model: str):
    class WeatherLookUp(BaseModel):
        """
        lookup the weather for the given location
        """

        location: str

    @dino(model, response_model=Iterable[WeatherLookUp])
    async def get_weather_info():
        return f"What's the weather like in San Francisco, London and Paris?"

    weather_info = await get_weather_info()
    assert len(weather_info) == 3
    locations = [info.location for info in weather_info]
    assert "San Francisco" in locations
    assert "London" in locations
    assert "Paris" in locations


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS)
async def test_after_hook(model: str):
    @dtool
    async def get_weather(location: str) -> str:
        return f"The weather in {location} is sunny"

    def after_hook(response: str):
        if response == "sunny":
            return "has sun shining"
        return "has no sun"

    @dino(
        model,
        tools=[get_weather],
        response_model=Literal["sunny", "cloudy"],
        after_hook=after_hook,
    )
    async def get_weather_info(location: str):
        return f"What is the weather in {location}?"

    assert await get_weather_info("San Francisco") == "has sun shining"


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS)
async def test_dino_with_after_hook_async(model: str):
    @dtool
    async def get_weather(location: str) -> str:
        return f"The weather in {location} is sunny"

    async def after_hook(response: str):
        if response == "sunny":
            return "has sun shining"
        return "has no sun"

    @dino(
        model,
        tools=[get_weather],
        response_model=Literal["sunny", "cloudy"],
        after_hook=after_hook,
    )
    async def get_weather_info(location: str):
        return f"What is the weather in {location}?"

    assert await get_weather_info("San Francisco") == "has sun shining"


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS)
async def test_dino_with_complicated_hook(model: str):
    @dtool
    async def get_weather(location: str) -> str:
        return f"sunny"

    async def after_hook(location: str, response: str):
        return f"The weather in {location} is {response}"

    @dino(
        model,
        tools=[get_weather],
        response_model=Literal["sunny", "cloudy"],
        after_hook=after_hook,
    )
    async def get_weather_info(location: str):
        return f"What is the weather in {location}?"

    assert (
        await get_weather_info("San Francisco")
        == "The weather in San Francisco is sunny"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS)
async def test_dino_with_after_hook_returns_none(model: str):
    @dtool
    def get_weather(location: str) -> str:
        return "sunny"

    async def after_hook(location: str, response: str):
        return None

    @dino(model, tools=[get_weather], response_model=Literal["sunny", "cloudy"])
    async def get_weather_info(location: str):
        return f"What is the weather in {location}?"

    assert await get_weather_info("San Francisco") == "sunny"


@pytest.mark.asyncio
async def test_dino_after_hook_must_have_response_param():
    @dtool
    async def get_weather(location: str) -> str:
        return "sunny"

    async def after_hook(location: str):
        return None

    @dino(
        "gpt-4o-mini",
        tools=[get_weather],
        response_model=Literal["sunny", "cloudy"],
        after_hook=after_hook,
    )
    async def get_weather_info(location: str):
        return f"What is the weather in {location}?"

    with pytest.raises(ValueError):
        await get_weather_info("San Francisco")


@pytest.mark.asyncio
async def test_swap_model():
    brand = Literal["OpenAI", "Anthropic"]

    @dino("gpt-4o-mini", response_model=brand)
    async def get_llm_info():
        return f"who made you?"

    assert await get_llm_info() == "OpenAI"
    assert await get_llm_info(model="claude-3-5-sonnet-20241022") == "Anthropic"


@pytest.mark.asyncio
async def test_dino_with_func_tools():
    @dtool
    async def get_weather(location: str) -> str:
        return f"The weather in {location} is sunny"

    @dtool
    async def get_weather_v2(location: str) -> str:
        return f"The weather in {location} is cloudy"

    @dino(
        "gpt-4o-mini",
        tools=[get_weather, get_weather],
        response_model=Literal["sunny", "cloudy"],
    )
    async def get_weather_info(location: str):
        """
        you answer the question about the weather in the given location.
        """
        return f"What is the weather in {location}?"

    assert await get_weather_info("San Francisco", tools=[get_weather_v2]) == "cloudy"


@pytest.mark.asyncio
async def test_dino_with_func_context():
    class Brand(BaseModel):
        brand: Literal["OpenAI", "Anthropic"]

        @model_validator(mode="after")
        def validate_brand(cls, v: str, info: ValidationInfo):
            brand = info.context.get("brand")
            if brand:
                v.brand = brand
            return v

    @dino("gpt-4o-mini", response_model=Brand)
    async def get_llm_info(context):
        return f"who made you?"

    info = await get_llm_info(context={"brand": "Anthropic"})
    assert info.brand == "Anthropic"


@pytest.mark.asyncio
async def test_dino_with_decorator_context():
    class Brand(BaseModel):
        brand: Literal["OpenAI", "Anthropic"]

        @model_validator(mode="after")
        def validate_brand(cls, v: str, info: ValidationInfo):
            brand = info.context.get("brand")
            if brand:
                v.brand = brand
            return v

    @dino("gpt-4o-mini", response_model=Brand, context={"brand": "Anthropic"})
    async def get_llm_info():
        return f"who made you?"

    info = await get_llm_info()
    assert info.brand == "Anthropic"


@pytest.mark.asyncio
async def test_gpt_o3_support_from_decorator():
    class UserInfo(BaseModel):
        name: str
        email: str

    client = instructor.from_openai(AsyncOpenAI(), mode=instructor.Mode.JSON_O1)

    @dino("o3-mini", response_model=UserInfo, client=client)
    async def get_llm_info(text: str):
        """
        You are a helpful assistant
        """
        return f"extract the user info: {text}"

    user_info = await get_llm_info(
        "My name is John Doe and my email is john.doe@example.com"
    )
    assert user_info.name == "John Doe"
    assert user_info.email == "john.doe@example.com"


@pytest.mark.asyncio
async def test_gpt_o3_support_out_of_box():
    class UserInfo(BaseModel):
        name: str
        email: str

    @dino("o3-mini", response_model=UserInfo)
    async def get_llm_info(text: str):
        """
        You are a helpful assistant
        """
        return f"extract the user info: {text}"

    user_info = await get_llm_info(
        "My name is John Doe and my email is john.doe@example.com",
    )
    assert user_info.name == "John Doe"
    assert user_info.email == "john.doe@example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS)
async def test_dino_with_context(model: str):
    @dtool
    async def get_weather(location: str, context: dict[str, Any] = {}) -> str:
        return f"The weather in {location} is {context[location]}"

    @dino(
        model,
        tools=[get_weather],
        response_model=Literal["sunny", "cloudy"],
    )
    async def get_weather_info(location: str, context: dict[str, Any] = {}):
        """
        you answer the question about the weather in the given location using tool calls
        """
        return f"What is the weather in {location}?"

    weather_lookup = {
        "San Francisco": "sunny",
        "London": "cloudy",
    }

    assert await get_weather_info("San Francisco", context=weather_lookup) == "sunny"
    assert await get_weather_info("London", context=weather_lookup) == "cloudy"


CAT_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/b/b5/1dayoldkitten.JPG"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        "gpt-4o-mini",
        "claude-3-5-sonnet-20241022",
    ],
)
async def test_vision_support(model: str):
    @dino(
        model,
        response_model=Literal["noimage", "dog", "cat", "ant"],
    )
    async def classify_image(image_url: str):
        """
        you are a helpful assistant that can classify images
        """
        return [Message.user(Message.image_url_content(image_url))]

    assert await classify_image(CAT_IMAGE_URL) == "cat"

    # comment out as big token assumption to upload base64 image
    # @dino(model, response_model=Literal["cat", "dog"])
    # async def classify_image_content(image_base64: str):
    #     """
    #     you are a helpful assistant that can classify images
    #     """
    #     return Message.user(Message.image_base64_content(image_base64))

    # image_base64 = base64.urlsafe_b64encode(httpx.get(CAT_IMAGE_URL).content).decode()
    # assert await classify_image_content(image_base64) == "cat"


@pytest.mark.asyncio
async def test_tool_calls_only():
    @dtool
    async def get_weather(location: str) -> str:
        return f"The weather in {location} is sunny"

    class Output(ResponseWithToolOutputs[ToolCall]):
        pass

    print(hasattr(Output, "tool_outputs"))

    @dino(
        "gpt-4o-mini",
        tools=[get_weather],
        response_model=Output,
    )
    async def get_weather_info(location: str):
        return f"What is the weather in {location}?"

    output = await get_weather_info("San Francisco", tool_calls_only=True)
    assert len(output.tool_outputs) == 1
    assert output.tool_outputs[0].output == "The weather in San Francisco is sunny"
    assert output.tool_outputs[0].location == "San Francisco"


@pytest.mark.asyncio
async def test_tool_calls_only_with_invalid_response_model():
    @dtool
    async def get_weather(location: str) -> str:
        return f"The weather in {location} is sunny"

    class Output(BaseModel):
        pass

    with pytest.raises(ValueError):

        @dino(
            "gpt-4o-mini",
            tools=[get_weather],
            response_model=Output,
        )
        async def get_weather_info(location: str):
            return f"What is the weather in {location}?"

        await get_weather_info("San Francisco", tool_calls_only=True)
