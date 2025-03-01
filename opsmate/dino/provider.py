from abc import ABC, abstractmethod
from .types import Message
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

logger = structlog.get_logger(__name__)

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
    def default_client(cls) -> AsyncInstructor: ...

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


def register_provider(name: str):
    def wrapper(cls: Type[Provider]):
        Provider.providers[name] = cls
        return cls

    return wrapper


def discover_providers(group_name="opsmate.dino.providers"):
    for entry_point in pkg_resources.iter_entry_points(group_name):
        try:
            entry_point.load()
        except Exception as e:
            logger.info("Error loading provider", name=entry_point.name, error=e)


@register_provider("openai")
class OpenAIProvider(Provider):
    models = [
        "gpt-4o",
        "gpt-4o-mini",
        "o1-preview",
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
        client = client or cls.default_client()
        kwargs.pop("client", None)

        messages = [{"role": m.role, "content": m.content} for m in messages]

        model = kwargs.get("model")
        if model == "o1-preview":
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
    @cache
    def default_client(cls) -> AsyncInstructor:
        return instructor.from_openai(AsyncOpenAI())


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
        client = client or cls.default_client()
        kwargs.pop("client", None)
        messages = [{"role": m.role, "content": m.content} for m in messages]

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
    def default_client(cls) -> AsyncInstructor:
        return instructor.from_anthropic(AsyncAnthropic())


@register_provider("xai")
class XAIProvider(OpenAIProvider):
    DEFAULT_BASE_URL = "https://api.x.ai/v1"
    models = ["grok-2-1212"]

    @classmethod
    @cache
    def default_client(cls) -> AsyncInstructor:
        return instructor.from_openai(
            AsyncOpenAI(
                base_url=os.getenv("XAI_BASE_URL", cls.DEFAULT_BASE_URL),
                api_key=os.getenv("XAI_API_KEY"),
            )
        )
