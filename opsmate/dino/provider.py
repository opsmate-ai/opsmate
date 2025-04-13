from abc import ABC, abstractmethod
from .types import Message, TextContent, ImageURLContent, Content
import instructor
from instructor import AsyncInstructor
from typing import Any, Awaitable, TypeVar, List, Type
from instructor.client import T
from tenacity import AsyncRetrying
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from functools import cache
import os
import pkg_resources
import structlog
from pydantic import ValidationError
from opentelemetry import trace
from pprint import pformat

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer("dino.provider")

T = TypeVar("T")


class Provider(ABC):

    allowed_kwargs = [
        "model",
        "max_tokens",
        "temperature",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "system",
    ]

    @classmethod
    @abstractmethod
    async def chat_completion(
        cls,
        response_model: type[T],
        messages: List[Message],
        max_retries: int | AsyncRetrying = 3,
        validation_context: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,  # {{ edit_1 }}
        strict: bool = True,
        client: AsyncInstructor | None = None,
        **kwargs: Any,
    ) -> Awaitable[T]: ...

    @classmethod
    @abstractmethod
    def _default_client(cls) -> AsyncInstructor: ...

    providers: dict[str, Type["Provider"]] = {}

    @classmethod
    def from_model(cls, model: str) -> "Provider":
        for provider in cls.providers.values():
            if model in provider.models:
                return provider
        raise ValueError(f"No provider found for model: {model}")

    @classmethod
    def _filter_kwargs(cls, kwargs: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in kwargs.items() if k in cls.allowed_kwargs}

    @classmethod
    @cache
    def default_client(cls, model: str) -> AsyncInstructor:
        client = cls._default_client()
        client.on("parse:error", cls._handle_parse_error)
        return client

    @classmethod
    def _handle_parse_error(cls, e: Exception):
        with tracer.start_as_current_span("dino.provider.handle_parse_error") as span:
            span.set_attribute("error", str(e))
            span.set_attribute("error_type", e.__class__.__name__)

            if isinstance(e, ValidationError):
                span.set_attribute("error_details", pformat(e.errors()))
                logger.debug("Validation error", error=e.errors())


def register_provider(name: str):
    def wrapper(cls: Type[Provider]):
        Provider.providers[name] = cls
        return cls

    return wrapper


def discover_providers(group_name="opsmate.dino.providers"):
    for entry_point in pkg_resources.iter_entry_points(group_name):
        try:
            cls = entry_point.load()
            if not issubclass(cls, Provider):
                logger.error(
                    "Provider must inherit from the Provider class",
                    name=entry_point.name,
                )
                continue
        except Exception as e:
            logger.error("Error loading provider", name=entry_point.name, error=e)


@register_provider("openai")
class OpenAIProvider(Provider):
    chat_models = ["gpt-4o", "gpt-4o-mini"]
    reasoning_models = ["o1", "o3-mini"]
    models = chat_models + reasoning_models

    @classmethod
    async def chat_completion(
        cls,
        response_model: type[T],
        messages: List[Message],
        max_retries: int | AsyncRetrying = 3,
        validation_context: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,  # {{ edit_1 }}
        strict: bool = True,
        client: AsyncInstructor | None = None,
        **kwargs: Any,
    ) -> Awaitable[T]:
        model = kwargs.get("model")
        client = client or cls.default_client(model)
        kwargs.pop("client", None)

        messages = [
            {"role": m.role, "content": cls.normalise_content(m.content)}
            for m in messages
        ]

        if cls.is_reasoning_model(model):
            # modify all the system messages to be user
            for message in messages:
                if message["role"] == "system":
                    message["role"] = "user"
        filtered_kwargs = cls._filter_kwargs(kwargs)
        return await client.chat.completions.create(
            response_model=response_model,
            messages=messages,
            max_retries=max_retries,
            validation_context=validation_context,
            context=context,
            strict=strict,
            **filtered_kwargs,
        )

    @classmethod
    def _default_client(cls) -> AsyncInstructor:
        return instructor.from_openai(AsyncOpenAI())

    @classmethod
    def _default_reasoning_client(cls) -> AsyncInstructor:
        return instructor.from_openai(AsyncOpenAI(), mode=instructor.Mode.JSON_O1)

    @classmethod
    @cache
    def default_client(cls, model: str) -> AsyncInstructor:
        if cls.is_reasoning_model(model):
            return cls._default_reasoning_client()
        else:
            return cls._default_client()

    @classmethod
    def is_reasoning_model(cls, model: str) -> bool:
        return model in cls.reasoning_models

    @staticmethod
    def normalise_content(content: Content):
        match content:
            case str():
                return content
            case list():
                result = []
                for item in content:
                    match item:
                        case TextContent():
                            result.append({"type": "text", "text": item.text})
                        case ImageURLContent():
                            if item.image_url:
                                result.append(
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": item.image_url,
                                            "detail": item.detail,
                                        },
                                    }
                                )
                            elif item.image_base64:
                                result.append(
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/{item.image_type};base64,{item.image_base64}",
                                            # "detail": item.detail,
                                        },
                                    }
                                )
                            else:
                                raise ValueError("Invalid image content")
                return result


@register_provider("anthropic")
class AnthropicProvider(Provider):
    models = [
        "claude-3-5-sonnet-20241022",
        "claude-3-7-sonnet-20250219",
    ]

    @classmethod
    async def chat_completion(
        cls,
        response_model: type[T],
        messages: List[Message],
        max_retries: int | AsyncRetrying = 3,
        validation_context: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,  # {{ edit_1 }}
        strict: bool = True,
        client: AsyncInstructor | None = None,
        **kwargs: Any,
    ) -> Awaitable[T]:
        model = kwargs.get("model")
        client = client or cls.default_client(model)
        kwargs.pop("client", None)
        messages = [
            {"role": m.role, "content": cls.normalise_content(m.content)}
            for m in messages
        ]

        # filter out all the system messages
        sys_messages = [m for m in messages if m["role"] == "system"]
        messages = [m for m in messages if m["role"] != "system"]

        sys_prompt = "\n".join([m["content"] for m in sys_messages])

        if len(sys_messages) > 0:
            kwargs["system"] = sys_prompt

        if kwargs.get("max_tokens") is None:
            kwargs["max_tokens"] = 1000

        filtered_kwargs = cls._filter_kwargs(kwargs)
        return await client.chat.completions.create(
            response_model=response_model,
            messages=messages,
            max_retries=max_retries,
            validation_context=validation_context,
            context=context,
            strict=strict,
            **filtered_kwargs,
        )

    @classmethod
    @cache
    def _default_client(cls) -> AsyncInstructor:
        return instructor.from_anthropic(AsyncAnthropic())

    @staticmethod
    def normalise_content(content: Content):
        match content:
            case str():
                return content
            case list():
                result = []
                for item in content:
                    match item:
                        case TextContent():
                            result.append({"type": "text", "text": item.text})
                        case ImageURLContent():
                            if item.image_url:
                                result.append(
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "url",
                                            "url": item.image_url,
                                        },
                                    }
                                )
                            elif item.image_base64:
                                result.append(
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": f"image/{item.image_type}",
                                            "data": item.image_base64,
                                        },
                                    }
                                )
                            else:
                                raise ValueError("Invalid image content")
                return result


@register_provider("xai")
class XAIProvider(OpenAIProvider):
    DEFAULT_BASE_URL = "https://api.x.ai/v1"
    chat_models = [
        "grok-2-1212",
        "grok-2-vision-1212",
    ]
    reasoning_models = [
        "grok-3-mini-fast-beta",
        "grok-3-mini-beta",
        "grok-3-fast-beta",
        "grok-3-beta",
    ]
    models = chat_models + reasoning_models

    @classmethod
    @cache
    def _default_client(cls) -> AsyncInstructor:
        return instructor.from_openai(
            AsyncOpenAI(
                base_url=os.getenv("XAI_BASE_URL", cls.DEFAULT_BASE_URL),
                api_key=os.getenv("XAI_API_KEY"),
            ),
        )

    @classmethod
    def _default_reasoning_client(cls) -> AsyncInstructor:
        return instructor.from_openai(
            AsyncOpenAI(
                base_url=os.getenv("XAI_BASE_URL", cls.DEFAULT_BASE_URL),
                api_key=os.getenv("XAI_API_KEY"),
            ),
            mode=instructor.Mode.JSON_O1,
        )

    @classmethod
    def is_reasoning_model(cls, model: str) -> bool:
        return model in cls.reasoning_models
