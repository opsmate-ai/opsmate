from typing import List, Callable, ParamSpec, Dict, Awaitable, ClassVar, Type
from opsmate.dino.types import Context, ToolCall
import asyncio
import importlib
import inspect
import structlog
from pydantic import BaseModel
import os
import sys

logger = structlog.get_logger(__name__)
P = ParamSpec("P")


class ContextRegistry(BaseModel):
    _contexts: ClassVar[Dict[str, Context]] = {}
    _context_sources: ClassVar[Dict[str, str]] = {}

    @classmethod
    def context(
        cls, name: str, tools: List[Type[ToolCall]] = [], contexts: List[Context] = []
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
                description=inspect.getdoc(fn) if fn.__doc__ else "",
                contexts=contexts,
                tools=tools,
            )

        return wrapper

    @classmethod
    def discover(cls, *context_dirs: str, ignore_conflicts: bool = False):
        """discover contexts in a directory"""
        cls.load_builtin(ignore_conflicts=ignore_conflicts)
        for context_dir in context_dirs:
            cls._discover(context_dir, ignore_conflicts)

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
    def _discover(cls, context_dir: str, ignore_conflicts: bool = False):
        """discover contexts in a directory"""

        if not os.path.exists(context_dir):
            logger.warning("Context directory does not exist", context_dir=context_dir)
            return

        logger.info(
            "adding the context directory to the sys path",
            context_dir=os.path.abspath(context_dir),
        )
        sys.path.append(os.path.abspath(context_dir))

        for filename in os.listdir(context_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                context_path = os.path.join(context_dir, filename)
                cls._load_context_file(context_path, ignore_conflicts)

        sys.path.remove(os.path.abspath(context_dir))

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
    def _load_context_file(cls, context_path: str, ignore_conflicts: bool = False):
        """load a context file"""
        logger.info("loading context file", context_path=context_path)
        try:
            module_name = os.path.basename(context_path).replace(".py", "")
            spec = importlib.util.spec_from_file_location(module_name, context_path)

            if spec is None or spec.loader is None:
                logger.error("failed to load context file", context_path=context_path)
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            cls._load_contexts(module, ignore_conflicts)

            logger.info("loaded context file", context_path=context_path)
        except Exception as e:
            logger.error(
                "failed to load context file", context_path=context_path, error=e
            )
            if not ignore_conflicts:
                raise e

    @classmethod
    def get_context(cls, name: str) -> Context:
        return cls._contexts.get(name, None)

    @classmethod
    def get_contexts(cls) -> Dict[str, Context]:
        return cls._contexts

    @classmethod
    def reset(cls):
        cls._contexts = {}
        cls._context_sources = {}


context = ContextRegistry.context
