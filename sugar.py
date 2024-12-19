from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import subprocess

from opsmate.dino import dino, dtool, run_react
from opsmate.dino.types import Message
import structlog

logger = structlog.get_logger(__name__)


class ShellCommand(BaseModel):
    """
    The command to run
    """

    command: str = Field(description="The command to run")
    output: Optional[str] = None

    def __call__(self):
        logger.info("running shell command", command=self.command)
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


@dtool
def run_command(command: str) -> str:
    return ShellCommand(command=command)()


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
    result = await bob("tell a joke that mentions your name")
    print(result)

    user_info = await get_user_info(
        "User Jingkai He has an email jingkai.he@example.com"
    )

    assert user_info.name == "Jingkai He"
    assert user_info.email == "jingkai.he@example.com"

    hello = await say_hello("Jingkai He")
    print(hello)

    shell_command = await run_shell_command("what's the operating system?")
    print(shell_command().lower())

    birthday = await get_birthday("Jingkai He and Boris Johnson")
    print(birthday)

    async for result in run_react(
        "how many cpus do the vm have?",
        pretext="you are a agent running on a ubuntu 24.04 vm",
        tools=[run_command],
    ):
        print(result)


if __name__ == "__main__":

    asyncio.run(main())
