import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, create_model
from typing import Any, Callable, Optional, List, Union, Iterable, Coroutine
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
                        if inspect.iscoroutinefunction(resp.__call__):
                            await resp.__call__()
                        else:
                            resp.__call__()
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


def dtool(fn: Callable | Coroutine[Any, Any, Any]):
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


class React(BaseModel):
    thoughts: str = Field(description="Your thought about the question")
    action: str = Field(description="Action to take based on your thoughts")


class ReactAnswer(BaseModel):
    answer: str = Field(description="Your final answer to the question")


class Observation(BaseModel):
    observation: str = Field(description="The observation of the action")


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


@dino("gpt-4o", response_model=Union[React, ReactAnswer])
async def react(question: str, context: List[Message]):
    """
    <assistant>
    You run in a loop of question, thought, action.
    At the end of the loop you output an answer.
    Use "Question" to describe the question you have been asked.
    Use "Thought" to describe your thought
    Use "Action" to describe the action you are going to take based on the thought.
    Use "Answer" as the final answer to the question.
    </assistant>

    <response format 1>
    During the thought phase you response with the following format:
    thought: ...
    action: ...
    </response_format 1>

    <response format 2>
    When you have an answer, you response with the following format:
    answer: ...
    </response_format 2>
    """

    return [
        Message(role="user", content=question),
        *context,
    ]


@dtool
def run_command(command: str) -> str:
    return ShellCommand(command=command)()


async def run_react(
    question: str,
    pretext: str = "",
    tools: List[BaseModel] = [],
):

    @dino("gpt-4o-mini", response_model=Observation, tools=tools)
    async def run_action(react: React):
        return [
            Message(role="system", content=pretext),
            Message(role="assistant", content=react.model_dump_json()),
        ]

    context = []
    if pretext:
        context.append(Message(role="system", content=pretext))
    while True:
        react_result = await react(question, context)
        if isinstance(react_result, React):
            context.append(
                Message(role="assistant", content=react_result.model_dump_json())
            )
            yield react_result
            observation = await run_action(react_result)
            context.append(
                Message(role="assistant", content=observation.model_dump_json())
            )
            yield observation
        elif isinstance(react_result, ReactAnswer):
            yield react_result
            break


@dino("gpt-4o-mini", response_model=str)
async def say_hello(name: str):
    return f"just say hi to {name}"


### Abitrary Tool calling example
@dino("gpt-4o-mini", response_model=ShellCommand)
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
async def birthday_lookup(person_name: str) -> str:
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


class UserInfo(BaseModel):
    name: str = Field(description="The name of the user")
    email: str = Field(description="The email of the user")


### Information Extraction example
@dino("gpt-4o-mini", response_model=UserInfo)
async def get_user_info(text: str):
    return f"extract the username and email from {text}"


@dtool
@dino("gpt-4o-mini", response_model=str)
async def alice(instruction: str) -> str:
    """
    Your name is Alice, you are a personal assistant.
    """
    return "please do the following: " + instruction


@dino("gpt-4o-mini", response_model=str, tools=[alice])
async def bob(instruction: str):
    return "delegate the following instruction: " + instruction


async def main():
    # result = await bob("tell a joke that mentions your name")
    # print(result)

    # user_info = await get_user_info(
    #     "User Jingkai He has an email jingkai.he@example.com"
    # )

    # assert user_info.name == "Jingkai He"
    # assert user_info.email == "jingkai.he@example.com"

    # hello = await say_hello("Jingkai He")
    # print(hello)

    # shell_command = await run_shell_command("what's the operating system?")
    # print(shell_command().lower())

    # birthday = await get_birthday("Jingkai He and Boris Johnson")
    # print(birthday)

    async for result in run_react(
        "how many pods are in the cluster?",
        pretext="you have kubectl command to run",
        tools=[run_command],
    ):
        print(result)


if __name__ == "__main__":

    asyncio.run(main())
