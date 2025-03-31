from abc import ABC, abstractmethod
from typing import Type
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field

import pkg_resources
import structlog

logger = structlog.get_logger(__name__)


class RuntimeConfig(BaseSettings):
    model_config = ConfigDict(populate_by_name=True)


class Runtime(ABC):
    runtimes: dict[str, Type["Runtime"]] = {}
    configs: dict[str, Type[RuntimeConfig]] = {}

    @abstractmethod
    async def run(self, *args, **kwargs):
        pass

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def disconnect(self):
        pass


class RuntimeError(Exception): ...


def register_runtime(name: str, config: Type[RuntimeConfig]):
    def wrapper(cls: Type[Runtime]):
        Runtime.runtimes[name] = cls
        Runtime.configs[name] = config

        return cls

    return wrapper


def discover_runtimes(group_name="opsmate.runtime.runtimes"):
    for entry_point in pkg_resources.iter_entry_points(group_name):
        try:
            cls = entry_point.load()
            if not issubclass(cls, Runtime):
                logger.error(
                    "Runtime must inherit from the Runtime class", name=entry_point.name
                )
                continue
        except Exception as e:
            logger.error("Error loading runtime", name=entry_point.name, error=e)
