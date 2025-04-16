from .base import register_provider
from .openai import OpenAIProvider
from instructor import AsyncInstructor
from openai import AsyncOpenAI
from functools import cache
import os
import instructor


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
