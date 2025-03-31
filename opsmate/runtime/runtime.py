from abc import ABC, abstractmethod
from typing import Type, Dict
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import wraps
import click
import pkg_resources
import structlog

logger = structlog.get_logger(__name__)


class CommaSeparatedList(click.Option):
    """Custom Click option for handling comma-separated lists.

    This class allows you to pass comma-separated values to a Click option
    and have them automatically converted to a Python list.

    Example usage:
        @click.option('--items', cls=CommaSeparatedList)
        def command(items):
            # items will be a list
    """

    def type_cast_value(self, ctx, value):
        if value is None or value == "":
            return []

        # Handle the case where the value is already a list
        if isinstance(value, list) or isinstance(value, tuple):
            return value

        # Split by comma and strip whitespace
        result = [item.strip() for item in value.split(",") if item.strip()]
        return result

    def get_help_record(self, ctx):
        help_text = self.help or ""
        if help_text and not help_text.endswith("."):
            help_text += "."
        help_text += " Values should be comma-separated."

        return super(CommaSeparatedList, self).get_help_record(ctx)


class RuntimeConfig(BaseSettings):
    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def config_params(cls):
        """Decorator to inject pydantic settings config as the click options."""

        def decorator(func):
            # do not use __annotations__ as it does not include the field metadata from the parent class
            config_fields = cls.model_fields

            # For each field, create a Click option
            for field_name, field_info in config_fields.items():
                # get the metadata
                field_info = cls.model_fields.get(field_name)
                if not field_info:
                    continue

                field_type = field_info.annotation
                if field_type in (Dict, list, tuple) or "Dict[" in str(field_type):
                    continue
                default_value = field_info.default
                is_type_iterable = isinstance(default_value, list) or isinstance(
                    default_value, tuple
                )
                if is_type_iterable:
                    default_value = ",".join(default_value)
                description = field_info.description or f"Set {field_name}"
                env_var = field_info.alias

                alias = field_info.alias.lower().replace("_", "-")
                option_name = f"--{alias}"
                func = click.option(
                    option_name,
                    default=default_value,
                    help=f"{description} (env: {env_var})",
                    show_default=True,
                    cls=CommaSeparatedList if is_type_iterable else None,
                )(func)

            def config_from_kwargs(kwargs):
                cfg = {}
                for field_name, field_info in config_fields.items():
                    alias = field_info.alias.lower()
                    if alias in kwargs:
                        value = kwargs.pop(alias)
                        cfg[field_name] = value

                return cls(**cfg)

            @wraps(func)
            def wrapper(*args, **kwargs):
                config_name = cls.__name__
                kwargs[config_name] = config_from_kwargs(kwargs)

                return func(*args, **kwargs)

            return wrapper

        return decorator


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

    @abstractmethod
    async def os_info(self):
        pass

    @abstractmethod
    async def whoami(self):
        pass

    @abstractmethod
    async def runtime_info(self):
        pass

    @abstractmethod
    async def has_systemd(self):
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
