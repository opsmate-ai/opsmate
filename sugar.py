import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, create_model
from typing import Any, Callable, Optional, List, Union, Iterable
from functools import wraps
import asyncio
import inspect
from inspect import Parameter

client = instructor.from_openai(AsyncOpenAI())


class Message(BaseModel):
    role: str = Field(description="The role of the message")
    content: str = Field(description="The content of the message")


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

            if tools:
                initial_response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_model=Iterable[Union[tuple(tools)]],
                )
                for resp in initial_response:
                    if isinstance(resp, BaseModel):
                        resp()
                        messages.append(
                            {"role": "user", "content": resp.model_dump_json()}
                        )

            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                response_model=response_model,
            )

            return response

        return wrapper

    return wrapper


def dtool(fn: Callable):
    """
    dtool is a decorator that turns a function into a Pydantic model.

    Example:

    @dtool
    def say_hello(name: Field(description="The name of the person to say hello to")):
        return f"say hi to {name}"

    Becomes:

    class SayHello(BaseModel):
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
    assert fn.__annotations__.get("return") == str, "fn must return a string"
    # add output field
    kw["output"] = (Optional[str], None)
    m = create_model(fn.__name__, **kw)

    # patch the __call__ method
    def call(self):
        s = self.model_dump()
        s.pop("output")
        self.output = fn(**s)
        return self.output

    m.__call__ = call

    return m


class UserInfo(BaseModel):
    name: str = Field(description="The name of the user")
    email: str = Field(description="The email of the user")


import subprocess


class ShellCommand(BaseModel):
    """
    The command to run
    """

    command: str = Field(description="The command to run")
    output: Optional[str] = None

    def __call__(self):
        try:
            result = subprocess.run(
                self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.output = result.stdout
        except subprocess.SubprocessError as e:
            self.output = str(e)
        return self.output


@dino("gpt-4o-mini", response_model=str)
async def say_hello(name: str):
    return f"just say hi to {name}"


### Information Extraction example
@dino("gpt-4o-mini", response_model=UserInfo)
async def get_user_info(text: str):
    return f"extract the username and email from {text}"


### Abitrary Tool calling example
@dino("gpt-4o", response_model=ShellCommand)
async def run_shell_command(instruction: str):
    """
    You are a world class sysadmin who is good at running shell commands.
    You are currently accessing a VM.
    """
    return [
        Message(
            role="user", content="either run the shell command or answer I don't know"
        ),
        Message(role="user", content=instruction),
    ]


### function calling example
@dtool
def birthday_lookup(person_name: str) -> str:
    """
    The function looks up the birthday of the person.
    """
    if person_name == "Jingkai He":
        return "1990-11-01"
    else:
        return "I don't know"


@dino("gpt-4o-mini", response_model=str, tools=[birthday_lookup])
async def get_birthday(people: str):
    """
    Please look up the birthday via tool.
    **DO NOT** use your knowledge to answer.
    """
    return f"find out the birthday of {people}"


async def main():
    hello = await say_hello("Jingkai He")
    print(hello)

    user_info = await get_user_info(
        "User Jingkai He has an email jingkai.he@example.com"
    )

    assert user_info.name == "Jingkai He"
    assert user_info.email == "jingkai.he@example.com"

    shell_command = await run_shell_command("what's the operating system?")
    print(shell_command().lower())
    assert "linux" in shell_command().lower()

    birthday = await get_birthday("Jingkai He and Boris Johnson")

    print(birthday)


if __name__ == "__main__":

    asyncio.run(main())
