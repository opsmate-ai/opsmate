from opsmate.dino.provider import Provider, register_provider
from opsmate.dino.types import Message
from typing import Any, Awaitable, List
from instructor.client import T
from instructor import AsyncInstructor
from tenacity import AsyncRetrying
from functools import cache
from google import genai
import instructor


@register_provider("google-genai")
class GoogleGenAIProvider(Provider):
    models = [
        "gemini-2.5-pro-preview-03-25",
        "gemini-2.5-pro-exp-03-25",
        "gemini-2.0-flash-001",
        "gemini-2.0-flash-lite",
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

        messages = [{"role": m.role, "content": m.content} for m in messages]

        messages = [
            (
                {"role": "model", "content": m["content"]}
                if m["role"] == "assistant"
                else m
            )
            for m in messages
        ]

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
        return instructor.from_genai(
            genai.Client(vertexai=True),
            mode=instructor.Mode.GENAI_STRUCTURED_OUTPUTS,
            use_async=True,
        )
