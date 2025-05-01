from .base import Provider, register_provider, T
from typing import Any, Awaitable, List
from instructor import AsyncInstructor
from openai import AsyncOpenAI
from functools import cache
from tenacity import AsyncRetrying
from opsmate.dino.types import Message, TextContent, ImageURLContent, Content
import instructor


@register_provider("openai")
class OpenAIProvider(Provider):
    chat_models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
    ]
    reasoning_models = [
        "o1",
        "o3",
        "o3-mini",
        "o4-mini",
    ]
    models = chat_models + reasoning_models

    models_config = {
        "o4-mini": {
            "reasoning_effort": "medium",
            "tool_call_model": "gpt-4.1",
        },
        "o3-mini": {
            "reasoning_effort": "medium",
            "tool_call_model": "gpt-4.1",
        },
        "o1": {
            "reasoning_effort": "medium",
            "tool_call_model": "gpt-4.1",
        },
        "o3": {
            "reasoning_effort": "medium",
            "tool_call_model": "gpt-4.1",
        },
    }

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

        filtered_kwargs = cls._filter_kwargs(kwargs)
        if cls.is_reasoning_model(model):
            # modify all the system messages to be user
            for message in messages:
                if message["role"] == "system":
                    message["role"] = "user"

            reasoning_effort = kwargs.get("reasoning_effort", "medium")
            filtered_kwargs["reasoning_effort"] = reasoning_effort

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
            client = cls._default_reasoning_client()
        else:
            client = cls._default_client()

        client.on("parse:error", cls._handle_parse_error)
        return client

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
