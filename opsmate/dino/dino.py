from typing import Any, Callable, Coroutine, List, Union, Iterable
from pydantic import BaseModel
import inspect
from functools import wraps
from .provider import Provider
from .types import Message, ToolCall
from .utils import args_dump


def dino(
    model: str,
    response_model: Any,
    after_hook: Callable | Coroutine = None,
    tools: List[ToolCall] = [],
    **kwargs: Any,
):
    """
    dino (dino is not openai) is a decorator that makes it easier to use LLMs.

    Parameters:
        model:
            The LLM model to use. Conventionally the model provider is automatically detected from the model name.
        response_model:
            The model to use for the response.
        after_hook:
            A function or a coroutine to call against the response.
            If it is a coroutine, it will be awaited.
            If it is a function, it will be called synchronously.
            If the after_hook returns a non-None value, it will be returned instead of the original response.
            The after_hook must have `response` as a parameter.
        tools:
            A list of tools to use, the tool must be a list of ToolCall.
        **kwargs:
            Additional arguments to pass to the provider. It can be:
            - client: a custom client
            - max_tokens: required by Anthropic. It will be defaulted to 1000 if not provided.
            - temperature
            - top_p
            - frequency_penalty
            - presence_penalty
            - system: used by Anthropic as a system prompt.
            - context: a dictionary of context to pass for Pydantic model validation.
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
    >> UserInfo(name="John Doe", email="john.doe@example.com")
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

    def wrapper(fn: Callable):
        @wraps(fn)
        async def wrapper(*args, **fn_kwargs):
            _model = fn_kwargs.get("model") or model
            provider = Provider.from_model(_model)

            system_prompt = fn.__doc__
            # if is coroutine, await it
            if inspect.iscoroutinefunction(fn):
                prompt = await fn(*args, **fn_kwargs)
            else:
                prompt = fn(*args, **fn_kwargs)

            ikwargs = _instructor_kwargs(kwargs, fn_kwargs)
            ikwargs["model"] = _model

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
                raise ValueError("Prompt must be a string, BaseModel, or List[Message]")

            tool_outputs = []
            if tools:
                initial_response = await provider.chat_completion(
                    messages=messages,
                    response_model=Iterable[Union[tuple(tools)]],
                    **ikwargs,
                )
                for resp in initial_response:
                    if isinstance(resp, BaseModel):
                        if inspect.iscoroutinefunction(resp.__call__):
                            await resp.__call__()
                        else:
                            resp.__call__()
                        messages.append(Message.user(resp.model_dump_json()))
                        tool_outputs.append(resp)

            response = await provider.chat_completion(
                messages=messages,
                response_model=response_model,
                **ikwargs,
            )

            # check if response class has a tool_outputs field
            if hasattr(response, "tool_outputs"):
                response.tool_outputs = tool_outputs

            if not after_hook:
                return response

            _validate_after_hook(after_hook)

            hook_args, hook_kwargs = args_dump(fn, after_hook, args, fn_kwargs)
            hook_kwargs.update(response=response)

            if inspect.iscoroutinefunction(after_hook):
                transformed_response = await after_hook(*hook_args, **hook_kwargs)
            elif callable(after_hook):
                transformed_response = after_hook(*hook_args, **hook_kwargs)
            else:
                raise ValueError("after_hook must be a coroutine or a function")

            if transformed_response is not None:
                return transformed_response

            return response

        return wrapper

    return wrapper
