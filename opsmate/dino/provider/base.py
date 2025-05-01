from abc import ABC, abstractmethod
from typing import Any, Awaitable, TypeVar, List, Type
from instructor import AsyncInstructor
from pydantic import ValidationError
from tenacity import AsyncRetrying
from pprint import pformat
from opentelemetry import trace
from functools import cache
import pkg_resources
import json
from pathlib import Path
from opsmate.dino.types import Message

import structlog

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

    CACHE_DIR = Path.home() / ".cache" / "opsmate"

    @classmethod
    def _get_cached_models(cls) -> List[str]:
        """Read cached models from file."""
        if cls.MODELS_CACHE_FILE.exists():
            try:
                with open(cls.MODELS_CACHE_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Error loading cached models", error=e)
                return []
        return []

    @classmethod
    def _cache_models(cls, models: List[str]) -> None:
        """Cache models to file."""
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cls.MODELS_CACHE_FILE, "w") as f:
            json.dump(models, f)

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
    models_config: dict[str, dict[str, Any]] = {}

    @classmethod
    def all_models_config(cls) -> dict[str, dict[str, Any]]:
        result = {}
        for provider in cls.providers.values():
            result.update(provider.models_config)
        return result

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
        cls.MODELS_CACHE_FILE = Provider.CACHE_DIR / f"{name}_models.json"
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
