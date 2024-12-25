from functools import wraps
from typing import List

from opsmate.dino.types import Context, ToolCall


def context(name: str, tools: List[ToolCall] = [], contexts: List[str] = []):
    def wrapper(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            return Context(
                name=name,
                content=fn(*args, **kwargs),
                contexts=contexts,
                tools=tools,
            )

        return wrapped

    return wrapper
