from opsmate.dino.provider import Provider, register_provider
from opsmate.dino.types import Message
from typing import Any, Awaitable, List
from instructor.client import T
from instructor import AsyncInstructor
from tenacity import AsyncRetrying
from functools import cache
from groq import AsyncGroq
import instructor
import os


@register_provider("groq")
class GroqProvider(Provider):
    DEFAULT_BASE_URL = "https://api.groq.com"

    # Here is the full list of models that support tool use https://console.groq.com/docs/tool-use
    models = [
        "qwen-qwq-32b",
        "qwen-2.5-32b",
        "mistral-saba-24b",
        "deepseek-r1-distill-qwen-32b",
        "deepseek-r1-distill-llama-70b",
        "llama-3.3-70b-versatile",
        # commented out as it cannot reliably use tools
        # "llama-3.1-8b-instant",
        # "mixtral-8x7b-32768",
        # "gemma2-9b-it",
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
        return instructor.from_groq(
            AsyncGroq(
                base_url=os.getenv("GROQ_BASE_URL", cls.DEFAULT_BASE_URL),
                api_key=os.getenv("GROQ_API_KEY"),
            ),
            mode=instructor.Mode.JSON,
        )
