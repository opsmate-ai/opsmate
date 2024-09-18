import json
from functools import wraps
from opentelemetry import trace
import inspect
from typing import Callable


tracer = trace.get_tracer("opsmate")


def traceit(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        kvs = {}
        parameters = inspect.signature(func).parameters
        parameter_items = list(parameters.values())
        for idx, val in enumerate(args):
            if parameter_items[idx].annotation in (int, str, bool, float):
                kvs[parameter_items[idx].name] = val
            elif parameter_items[idx].annotation in (dict, list):
                kvs[parameter_items[idx].name] = json.dumps(val)

        for k, v in kwargs.items():
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
