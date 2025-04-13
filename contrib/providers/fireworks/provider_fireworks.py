from opsmate.dino.provider import Provider, register_provider
from opsmate.dino.types import Message
from typing import Any, Awaitable, List
from instructor.client import T
from instructor import AsyncInstructor
from tenacity import AsyncRetrying
from functools import cache
from fireworks.client import AsyncFireworks
import instructor
import os


@register_provider("fireworks")
class FireworksProvider(Provider):
    DEFAULT_BASE_URL = "https://api.fireworks.ai/inference/v1"

    models = [
        "accounts/fireworks/models/llama-v3p1-405b-instruct",
        "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "accounts/fireworks/models/deepseek-r1",
        "accounts/fireworks/models/deepseek-v3",
        "accounts/fireworks/models/deepseek-v3-0324",
        "accounts/fireworks/models/deepseek-r1-distill-llama-70b",
        "accounts/fireworks/models/qwen2p5-72b-instruct",
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
        return instructor.from_fireworks(
            AsyncFireworks(
                base_url=os.getenv("FIREWORKS_BASE_URL", cls.DEFAULT_BASE_URL),
                api_key=os.getenv("FIREWORKS_API_KEY"),
            ),
            mode=instructor.Mode.FIREWORKS_TOOLS,
        )
