from typing import Any, Callable, Optional, Coroutine, Type
from pydantic import create_model
import inspect
from inspect import Parameter
from .types import ToolCall


def dtool(fn: Callable | Coroutine[Any, Any, Any]) -> Type[ToolCall]:
    """
    dtool is a decorator that turns a function into a Pydantic model.

    Example:

    @dtool
    def say_hello(name: Field(description="The name of the person to say hello to")):
        return f"say hi to {name}"

    Becomes:

    class SayHello(ToolCall):
        name: str = Field(description="The name of the person to say hello to")
        output: Optional[str] = None

        def __call__(self) -> str:
            return f"say hi to {self.name}"
    """

    kw = {
        n: (o.annotation, ... if o.default == Parameter.empty else o.default)
        for n, o in inspect.signature(fn).parameters.items()
    }

    # make sure fn returns a string
    _validate_fn(fn)
    # add output field
    kw["output"] = (Optional[str | ToolCall], None)
    m = create_model(
        fn.__name__,
        __doc__=fn.__doc__,
        __base__=ToolCall,
        **kw,
    )

    # patch the __call__ method
    if inspect.iscoroutinefunction(fn):

        async def call(self):
            s = self.model_dump()
            s.pop("output")
            self.output = await fn(**s)
            return self.output

    else:

        def call(self):
            s = self.model_dump()
            s.pop("output")
            self.output = fn(**s)
            return self.output

    m.__call__ = call

    return m


def _validate_fn(fn: Callable | Coroutine[Any, Any, Any]):
    if not _is_fn_returning_str(fn) and not _is_fn_returning_base_model(fn):
        raise ValueError("fn must return a string or a subclass of ToolCall")


def _is_fn_returning_str(fn: Callable | Coroutine[Any, Any, Any]):
    return fn.__annotations__.get("return") == str


def _is_fn_returning_base_model(fn: Callable | Coroutine[Any, Any, Any]):
    return_type = fn.__annotations__.get("return")
    return isinstance(return_type, type) and issubclass(return_type, ToolCall)
