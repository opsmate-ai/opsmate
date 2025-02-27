from functools import wraps
from typing import List, Callable, TypeVar, ParamSpec

from opsmate.dino.types import Context, ToolCall

T = TypeVar("T")
P = ParamSpec("P")


def context(name: str, tools: List[ToolCall] = [], contexts: List[Context] = []):
    """context decorates a function into a Context object

    Usage:

    ```python
    @context(name="calc", tools=[calc])
    def use_calculator():
        return "don't do caculation yourself only use the calculator"
    ```

    This will create a Context object with the name "calc" and the tools [calc]

    You can also nest contexts:

    ```python
    @context(name="math-genius", contexts=[use_calculator()])
    def math_genius():
        return "you are a math genius"
    ```

    This will create a Context object with the name "math-genius" and the contexts [use_calculator()]

    """

    def wrapper(fn: Callable[P, T]) -> Callable[P, Context]:
        @wraps(fn)
        def wrapped(*args, **kwargs):
            return Context(
                name=name,
                system_prompt=fn(*args, **kwargs),
                contexts=contexts,
                tools=tools,
            )

        return wrapped

    return wrapper
