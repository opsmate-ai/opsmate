from functools import wraps
from typing import List, Callable, TypeVar, ParamSpec

from opsmate.dino.types import Context, ToolCall

T = TypeVar("T")
P = ParamSpec("P")


def context(name: str, tools: List[ToolCall] = [], contexts: List[str] = []):
    def wrapper(fn: Callable[P, T]) -> Callable[P, Context]:
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
