import json
from functools import wraps
from opentelemetry import trace
import inspect
from typing import Callable, Union


tracer = trace.get_tracer("opsmate")


def traceit(*args, exclude: list = []):
    """
    Decorator to trace function calls.

    Usage:

    @traceit # all arguments will be traced as attributes
    def my_function(a, b, c):
        pass

    @traceit(exclude=["b"]) # b will not be traced as an attribute
    def my_function(a, b, c):
        pass
    """
    if len(args) == 1 and callable(args[0]):
        return _traceit(args[0], exclude)
    elif len(args) == 0:

        def decorator(func: Callable):
            return _traceit(func, exclude)

        return decorator
    else:
        raise ValueError("Invalid arguments")


def _traceit(func: Callable, exclude: list = []):
    @wraps(func)
    def wrapper(*args, **kwargs):
        kvs = {}
        parameters = inspect.signature(func).parameters
        parameter_items = list(parameters.values())
        for idx, val in enumerate(args):
            if parameter_items[idx].name in exclude:
                continue
            if parameter_items[idx].annotation in (int, str, bool, float):
                kvs[parameter_items[idx].name] = val
            elif parameter_items[idx].annotation in (dict, list):
                kvs[parameter_items[idx].name] = json.dumps(val)

        for k, v in kwargs.items():
            if k in exclude:
                continue
            if isinstance(k, (int, str, bool, float)):
                kvs[k] = v
            elif isinstance(k, (dict, list)):
                kvs[k] = json.dumps(v)

        with tracer.start_as_current_span(func.__name__) as span:
            for k, v in kvs.items():
                span.set_attribute(f"{func.__name__}.{k}", v)

            if parameters.get("span") is not None:
                kwargs["span"] = span

            return func(*args, **kwargs)

    return wrapper
