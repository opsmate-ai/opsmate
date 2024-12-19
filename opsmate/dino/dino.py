from typing import Any, Callable, List, Union, Iterable
from pydantic import BaseModel
import inspect
from functools import wraps
from .provider import Provider
from .types import Message


def dino(
    model: str,
    response_model: Any,
    tools: List[BaseModel] = [],
    **kwargs: Any,
):
    """
    dino (dino is not openai) is a decorator that makes it easier to use LLMs.

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

    def instructor_kwargs(kwargs: dict, fn_kwargs: dict):
        kwargs.update(fn_kwargs)
        return kwargs

    def wrapper(fn: Callable):
        @wraps(fn)
        async def wrapper(*args, **fn_kwargs):
            _model = fn_kwargs.get("model") or model
            provider = Provider.from_model(_model)

            system_prompt = fn.__doc__
            prompt = await fn(*args, **fn_kwargs)

            fn_kwargs = instructor_kwargs(kwargs, fn_kwargs)
            fn_kwargs["model"] = _model

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
                    **fn_kwargs,
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
                **fn_kwargs,
            )

            # check if response class has a tool_outputs field
            if hasattr(response, "tool_outputs"):
                response.tool_outputs = tool_outputs

            return response

        return wrapper

    return wrapper
