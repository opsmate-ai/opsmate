from .base import register_provider
from .openai import OpenAIProvider
from instructor import AsyncInstructor
from openai import AsyncOpenAI, OpenAI
from functools import cache
import os
import httpx
import instructor


# to deal with the fact that @property on a classmethod is deprecated
class classproperty:
    def __init__(self, method=None):
        self.method = method

    def __get__(self, instance, cls=None):
        return self.method(cls)


@register_provider("ollama")
class OllamaProvider(OpenAIProvider):
    DEFAULT_BASE_URL = "http://localhost:11434/v1"

    @classproperty
    @cache
    def models(cls) -> list[str]:
        try:

            client = OpenAI(
                base_url=os.getenv("OLLAMA_BASE_URL", cls.DEFAULT_BASE_URL),
                # connection timeout isn't exactly respected, but it's the best we can do
                http_client=httpx.Client(timeout=httpx.Timeout(None, connect=0.1)),
            )
            models = client.models.list()
            model_ids = [model.id for model in models]
            cls._cache_models(model_ids)
            return model_ids
        except Exception as e:
            cached_models = cls._get_cached_models()
            return cached_models

    @classmethod
    @cache
    def default_client(cls, model: str) -> AsyncInstructor:
        client = instructor.from_openai(
            AsyncOpenAI(
                base_url=os.getenv("OLLAMA_BASE_URL", cls.DEFAULT_BASE_URL),
                api_key="ollama",
            ),
            mode=instructor.Mode.JSON,
        )
        client.on("parse:error", cls._handle_parse_error)
        return client
