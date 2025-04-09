from pydantic_settings import BaseSettings as _BaseSettings
import json
import os
from typing import Dict, Optional
import click
from functools import wraps
from pydantic import ConfigDict


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


class BaseSettings(_BaseSettings):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    def serialize_to_env(self):
        """Serialize the config to a dictionary of environment variables"""

        env_vars = {}

        for field_name, field_value in self.model_dump().items():
            if field_value is None:
                continue

            field_info = self.model_fields.get(field_name)
            alias = field_info.alias

            if isinstance(field_value, dict):
                env_vars[alias] = json.dumps(field_value)
            elif isinstance(field_value, list) or isinstance(field_value, tuple):
                env_vars[alias] = json.dumps(field_value)
            else:
                env_vars[alias] = str(field_value)

        for key, value in env_vars.items():
            os.environ[key] = value

    @classmethod
    def config_params(cls, config_name: Optional[str] = None):
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
                config_registry = cls.__base__.__name__
                _config_name = config_name or cls.__name__

                if config_registry not in kwargs:
                    kwargs[config_registry] = {}

                kwargs[config_registry][_config_name] = config_from_kwargs(kwargs)

                return func(*args, **kwargs)

            return wrapper

        return decorator
