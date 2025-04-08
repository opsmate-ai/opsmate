from typing import (
    Any,
    Callable,
    Optional,
    Coroutine,
    Type,
    ParamSpec,
    TypeVar,
    Awaitable,
)
from pydantic import create_model
import inspect
from inspect import Parameter
from .types import ToolCall, BaseModel
import pkg_resources
import traceback
import structlog

logger = structlog.get_logger(__name__)


P = ParamSpec("P")
T = TypeVar("T")


def dtool(fn: Callable[P, T] | Callable[P, Awaitable[T]]) -> Type[ToolCall]:
    """
    dtool is a decorator that turns a function into a Pydantic model.

    Example:

    @dtool
    def say_hello(name: Field(description="The name of the person to say hello to")):
        return f"say hi to {name}"

    Becomes:

    class SayHello(ToolCall[str]):
        name: str = Field(description="The name of the person to say hello to")

        async def __call__(self) -> str:
            return f"say hi to {self.name}"
    """

    kw = {
        n: (o.annotation, ... if o.default == Parameter.empty else o.default)
        for n, o in inspect.signature(fn).parameters.items()
    }

    # remove the context parameter so that it is not included in the pydantic model
    # this will be passed to the __call__ in the runtime
    kw.pop("context", None)

    # make sure fn returns a string
    _validate_fn(fn)
    # Determine the return type of the function
    return_type = fn.__annotations__.get("return", Optional[str | ToolCall])

    # Use the return type of fn for the output field
    kw["_output"] = (Optional[return_type], None)
    m = create_model(
        fn.__name__,
        __doc__=fn.__doc__,
        __base__=ToolCall,
        **kw,
    )

    assert "context" not in m.model_fields

    # patch the __call__ method
    if inspect.iscoroutinefunction(fn):

        async def call(self, context: dict[str, Any] = {}) -> T:
            s = self.model_dump()
            s.pop("output")
            if _fn_has_context(fn):
                s["context"] = context
            return await fn(**s)

    else:

        def call(self, context: dict[str, Any] = {}) -> T:
            s = self.model_dump()
            s.pop("output")
            if _fn_has_context(fn):
                s["context"] = context
            return fn(**s)

    m.__call__ = call

    return m


def _validate_fn(fn: Callable | Coroutine[Any, Any, Any]):
    if not _is_fn_returning_str(fn) and not _is_fn_returning_base_model(fn):
        raise ValueError("fn must return a string or a subclass of BaseModel")


def _is_fn_returning_str(fn: Callable | Coroutine[Any, Any, Any]):
    return fn.__annotations__.get("return") == str


def _fn_has_context(fn: Callable | Coroutine[Any, Any, Any]):
    sig = inspect.signature(fn)
    return "context" in sig.parameters


def _is_fn_returning_base_model(fn: Callable | Coroutine[Any, Any, Any]):
    return_type = fn.__annotations__.get("return")
    return isinstance(return_type, type) and issubclass(return_type, BaseModel)


def discover_tools(group_name="opsmate.tools"):
    """discover tools via entry points"""
    for entry_point in pkg_resources.iter_entry_points(group_name):
        try:
            cls = entry_point.load()
            if not issubclass(cls, ToolCall):
                logger.error("Tool must inherit from ToolCall", tool=entry_point.name)
                continue
        except Exception as e:
            logger.error(
                "Error loading tool",
                tool=entry_point.name,
                error=e,
                stacktrace=traceback.format_exc(),
            )
            continue
