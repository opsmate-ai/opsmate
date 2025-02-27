from functools import wraps
from typing import List, Callable, ParamSpec, Dict, Awaitable, ClassVar
from opsmate.dino.types import Context, ToolCall
import asyncio
import importlib
import inspect
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)
P = ParamSpec("P")


class ContextRegistry(BaseModel):
    _contexts: ClassVar[Dict[str, Context]] = {}
    _context_sources: ClassVar[Dict[str, str]] = {}

    @classmethod
    def context(
        cls, name: str, tools: List[ToolCall] = [], contexts: List[Context] = []
    ):
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

        def wrapper(fn: Callable[[], Awaitable[str]]) -> Context:
            if not asyncio.iscoroutinefunction(fn):
                raise ValueError("System prompt must be a coroutine function")

            return Context(
                name=name,
                system_prompt=fn,
                description=fn.__doc__,
                contexts=contexts,
                tools=tools,
            )

        return wrapper

    @classmethod
    def load_builtin(
        cls,
        ignore_conflicts: bool = True,
        builtin_modules: List[str] = ["opsmate.contexts"],
    ):
        for builtin_module in builtin_modules:
            module = importlib.import_module(builtin_module)
            cls._load_contexts(module, ignore_conflicts)

    @classmethod
    def _load_contexts(cls, module, ignore_conflicts: bool = False):
        for item_name, item in inspect.getmembers(module):
            if isinstance(item, Context):
                logger.debug("loading context", context_var_name=item_name)
                ctx_name = item.name
                if (
                    ctx_name in cls._contexts
                    and cls._context_sources[ctx_name] != module.__file__
                ):
                    conflict_source = cls._context_sources[ctx_name]
                    logger.warning(
                        "context already exists",
                        context=ctx_name,
                        conflict_source=conflict_source,
                    )
                    if not ignore_conflicts:
                        raise ValueError(
                            f"Context {ctx_name} already exists at {conflict_source}"
                        )
                cls._contexts[ctx_name] = item
                cls._context_sources[ctx_name] = module.__file__

    @classmethod
    def get_context(cls, name: str) -> Context:
        return cls._contexts[name]

    @classmethod
    def get_contexts(cls) -> List[Context]:
        return list(cls._contexts.values())


context = ContextRegistry.context
