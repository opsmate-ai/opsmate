from .base import Provider, register_provider, T
from instructor import AsyncInstructor
from anthropic import AsyncAnthropic
from typing import Any, Awaitable, List, Dict
from tenacity import AsyncRetrying
from opsmate.dino.types import Message, TextContent, ImageURLContent, Content
from functools import cache
import instructor


@register_provider("anthropic")
class AnthropicProvider(Provider):
    chat_completion_models = [
        "claude-3-5-sonnet-20241022",
    ]
    reasoning_models = [
        "claude-3-7-sonnet-20250219",
    ]
    models = chat_completion_models + reasoning_models

    models_config = {}

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
        thinking = kwargs.get("thinking", None)
        model = kwargs.get("model")
        client = client or cls.default_client(model, thinking)
        kwargs.pop("client", None)
        messages = [
            {"role": m.role, "content": cls.normalise_content(m.content)}
            for m in messages
        ]

        # filter out all the system messages
        sys_messages = [
            {"type": "text", "text": m["content"]}
            for m in messages
            if m["role"] == "system"
        ]
        messages = [m for m in messages if m["role"] != "system"]

        if len(sys_messages) > 0:
            sys_messages[-1]["cache_control"] = {"type": "ephemeral"}
            kwargs["system"] = sys_messages

        if kwargs.get("max_tokens") is None:
            kwargs["max_tokens"] = 8192

        filtered_kwargs = cls._filter_kwargs(kwargs)
        if thinking:
            filtered_kwargs["thinking"] = thinking

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

    @classmethod
    def _default_reasoning_client(cls) -> AsyncInstructor:
        return instructor.from_anthropic(
            AsyncAnthropic(), mode=instructor.Mode.ANTHROPIC_REASONING_TOOLS
        )

    @classmethod
    def is_reasoning_model(cls, model: str) -> bool:
        return model in cls.reasoning_models

    @classmethod
    def default_client(
        cls, model: str, thinking: Dict[str, Any] | None = None
    ) -> AsyncInstructor:
        if cls.is_reasoning_model(model) and thinking:
            client = cls._default_reasoning_client()
        else:
            client = cls._default_client()

        client.on("parse:error", cls._handle_parse_error)
        return client

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
