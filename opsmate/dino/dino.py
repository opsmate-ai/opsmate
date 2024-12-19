from typing import Any, Callable, List, Union, Iterable
from pydantic import BaseModel
from openai import AsyncOpenAI
import inspect
import instructor
from functools import wraps

from .types import Message, Result


client = instructor.from_openai(AsyncOpenAI())


def dino(
    model: str,
    response_model: Any,
    tools: List[BaseModel] = [],
    client: AsyncOpenAI = client,
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

    def wrapper(fn: Callable):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            system_prompt = fn.__doc__
            prompt = await fn(*args, **kwargs)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            if isinstance(prompt, str):
                messages.append({"role": "user", "content": prompt})
            elif isinstance(prompt, BaseModel):
                messages.append({"role": "user", "content": prompt.model_dump_json()})
            elif isinstance(prompt, list) and all(
                isinstance(m, Message) for m in prompt
            ):
                messages.extend(
                    [{"role": m.role, "content": m.content} for m in prompt]
                )
            else:
                raise ValueError("Prompt must be a string, BaseModel, or List[Message]")

            tool_outputs = []
            if tools:
                initial_response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_model=Iterable[Union[tuple(tools)]],
                )
                for resp in initial_response:
                    if isinstance(resp, BaseModel):
                        if inspect.iscoroutinefunction(resp.__call__):
                            await resp.__call__()
                        else:
                            resp.__call__()
                        messages.append(
                            {"role": "user", "content": resp.model_dump_json()}
                        )
                        tool_outputs.append(resp)

            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                response_model=response_model,
            )

            # check if response class has a tool_outputs field
            if hasattr(response, "tool_outputs"):
                response.tool_outputs = tool_outputs

            return response

        return wrapper

    return wrapper
