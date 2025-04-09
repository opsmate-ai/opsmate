from typing import (
    Any,
    Callable,
    Coroutine,
    List,
    Union,
    Iterable,
    ParamSpec,
    TypeVar,
    Awaitable,
    Type,
    Optional,
)
from pydantic import BaseModel
import inspect
from functools import wraps
from .provider import Provider
from .types import Message, ToolCall
from .utils import args_dump
import structlog
from instructor import AsyncInstructor
from tenacity import AsyncRetrying, stop_after_attempt, wait_fixed
from opentelemetry import trace
from opentelemetry.trace.status import Status, StatusCode
import asyncio

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer("opsmate.dino")

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")


def dino(
    model: str,
    response_model: Type[T],
    after_hook: Optional[Callable | Coroutine] = None,
    tools: List[ToolCall] = [],
    client: AsyncInstructor = None,
    **kwargs: Any,
):
    """
    Dino (Dino Is Not OpenAI) is a decorator to simplify the use of LLMs.

    Parameters:
        model (str):
            The LLM model to use. The model provider is typically inferred from the model name.
        response_model (Type[T]):
            The model to use for the response.
        after_hook (Callable | Coroutine, optional):
            A function or coroutine to process the response. If a coroutine, it will be awaited;
            if a function, it will be called synchronously. If it returns a non-None value,
            that value is returned instead of the original response. Must accept `response` as a parameter.
        tools (List[ToolCall], optional):
            A list of tools to use, each must be a ToolCall.
        client (AsyncInstructor, optional):
            A custom instructor.AsyncInstructor instance. e.g. `instructor.from_openai(AsyncOpenAI()`
        **kwargs (Any):
            Additional arguments for the provider, such as:
            - max_tokens: required by Anthropic, defaults to 1000 if not provided
            - temperature
            - top_p
            - frequency_penalty
            - presence_penalty
            - system: used by Anthropic as a system prompt
            - context: a dictionary for Pydantic model validation
            - max_retries: the number of retries for the tool call, defaults to 3
    Example:

    class UserInfo(BaseModel):
        name: str = Field(description="The name of the user")
        email: str = Field(description="The email of the user")

    @dino("gpt-4o", response_model=UserInfo)
    async def get_user_info(text: str):
        \"""
        You are a helpful assistant that extracts user information from a text.
        \"""
        return "extract the user info"

    user_info = await get_user_info("User John Doe has an email john.doe@example.com")
    print(user_info)
    # Output: UserInfo(name="John Doe", email="john.doe@example.com")
    """

    def _instructor_kwargs(kwargs: dict, fn_kwargs: dict):
        kwargs = kwargs.copy()
        fn_kwargs = fn_kwargs.copy()

        kwargs.update(fn_kwargs)
        return kwargs

    def _validate_after_hook(after_hook: Callable):
        params = inspect.signature(after_hook).parameters
        if "response" not in params:
            raise ValueError("after_hook must have `response` as a parameter")

    decorator_model = model
    decorator_tools = tools
    decorator_client = client

    def _get_model(model: str, decorator_model: str):
        if model:
            logger.debug(
                "Override the decorator model to the function model",
                model=model,
                decorator_model=decorator_model,
            )
            return model
        return decorator_model

    def _get_tools(tools: List[ToolCall], decorator_tools: List[ToolCall]):
        if tools and isinstance(tools, list):
            logger.debug(
                "Override the decorator tools to the function tools",
                tools=tools,
                decorator_tools=decorator_tools,
            )
            return tools
        return decorator_tools

    def _get_client(
        client: AsyncInstructor | None, decorator_client: AsyncInstructor | None
    ):
        if client:
            logger.debug(
                "Override the decorator client to the function client",
            )
            return client
        return decorator_client

    def wrapper(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[T]]:
        @wraps(fn)
        async def wrapper(
            *args: P.args,
            tools: List[ToolCall] = [],
            model: str = None,
            client: AsyncInstructor = None,
            tool_calls_only: bool = False,
            **fn_kwargs: P.kwargs,
        ):
            if tool_calls_only:
                if not hasattr(response_model, "tool_outputs"):
                    raise ValueError(
                        f"response_model {response_model} must have a tool_outputs field when tool_calls_only is True"
                    )
            with tracer.start_as_current_span(f"dino.{fn.__name__}") as fn_span:
                _model = _get_model(model, decorator_model)
                _tools = _get_tools(tools, decorator_tools)
                _client = _get_client(client, decorator_client)
                provider = Provider.from_model(_model)

                system_prompt = inspect.getdoc(fn) if fn.__doc__ else ""
                # if is coroutine, await it
                if inspect.iscoroutinefunction(fn):
                    prompt = await fn(*args, **fn_kwargs)
                else:
                    prompt = fn(*args, **fn_kwargs)

                ikwargs = _instructor_kwargs(kwargs, fn_kwargs)
                ikwargs["model"] = _model

                if fn_span.is_recording():
                    fn_span.set_attributes(
                        {
                            "dino.model": _model,
                            "dino.response_model": response_model.__name__,
                            "dino.tool_calls_only": tool_calls_only,
                            "dino.system_prompt": (
                                system_prompt if system_prompt else ""
                            ),
                            "dino.tool_calls": [tool.__name__ for tool in _tools],
                        }
                    )

                messages = []
                if system_prompt:
                    messages.append(Message.system(system_prompt))

                if isinstance(prompt, str):
                    messages.append(Message.user(prompt))
                elif isinstance(prompt, BaseModel):
                    messages.append(Message.user(prompt.model_dump_json()))
                elif isinstance(prompt, list) and all(
                    isinstance(m, Message) for m in prompt
                ):
                    messages.extend(prompt)
                else:
                    raise ValueError(
                        "Prompt must be a string, BaseModel, or List[Message]"
                    )

                tool_call_ctx = ikwargs.get("context", {})
                tool_call_ctx["dino_model"] = _model

                tool_outputs: List[ToolCall] = []
                if _tools:
                    with tracer.start_as_current_span(
                        "dino.tool_calls"
                    ) as tool_call_span:
                        initial_response = await provider.chat_completion(
                            messages=messages,
                            response_model=Iterable[Union[tuple(_tools)]],
                            client=_client,
                            max_retries=AsyncRetrying(
                                stop=stop_after_attempt(ikwargs.get("max_retries", 3)),
                                wait=wait_fixed(1),
                            ),
                            **ikwargs,
                        )

                        tool_call_span.set_attributes(
                            {
                                "dino.tools_returned": len(tool_outputs),
                                "dino.tools_returned_names": [
                                    tool_output.__class__.__name__
                                    for tool_output in tool_outputs
                                ],
                            }
                        )
                        tasks = []
                        for resp in initial_response:
                            tasks.append(resp.run(context=tool_call_ctx))

                        await asyncio.gather(*tasks)

                        for tool_output in initial_response:
                            logger.debug(
                                "Tool output", tool=tool_output.model_dump_json()
                            )
                            messages.append(Message.user(tool_output.prompt_display()))
                            tool_outputs.append(tool_output)

                with tracer.start_as_current_span("dino.response") as response_span:
                    if tool_calls_only:
                        response = response_model()
                        response.tool_outputs = tool_outputs
                    else:
                        response = await provider.chat_completion(
                            messages=messages,
                            response_model=response_model,
                            client=_client,
                            max_retries=AsyncRetrying(
                                stop=stop_after_attempt(ikwargs.get("max_retries", 3)),
                                wait=wait_fixed(1),
                            ),
                            **ikwargs,
                        )

                        if hasattr(response, "tool_outputs"):
                            assert (
                                response.tool_outputs == []
                            ), "must not hallucinate tool outputs"
                            response.tool_outputs = tool_outputs

                    if not after_hook:
                        fn_span.set_status(StatusCode.OK)
                        return response

                    with tracer.start_as_current_span(
                        "dino.after_hook"
                    ) as after_hook_span:
                        after_hook_span.set_attribute(
                            "dino.after_hook_type",
                            (
                                "coroutine"
                                if inspect.iscoroutinefunction(after_hook)
                                else "function"
                            ),
                        )
                        _validate_after_hook(after_hook)

                        hook_args, hook_kwargs = args_dump(
                            fn, after_hook, args, fn_kwargs
                        )
                        hook_kwargs.update(response=response)

                        if inspect.iscoroutinefunction(after_hook):
                            transformed_response = await after_hook(
                                *hook_args, **hook_kwargs
                            )
                        elif callable(after_hook):
                            transformed_response = after_hook(*hook_args, **hook_kwargs)
                        else:
                            raise ValueError(
                                "after_hook must be a coroutine or a function"
                            )

                        if transformed_response is not None:
                            after_hook_span.set_status(StatusCode.OK)
                            return transformed_response

                        after_hook_span.set_status(StatusCode.OK)
                        return response

        return wrapper

    return wrapper
