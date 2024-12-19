from pydantic import BaseModel, Field
from typing import Any, List, Optional


class Message(BaseModel):
    role: str = Field(description="The role of the message")
    content: str = Field(description="The content of the message")


class Result(BaseModel):
    result: Any = Field(description="The result of a dino run")
    tool_output: List[str | BaseModel] = Field(
        description="The output of the tools used in the dino run"
    )


class React(BaseModel):
    thoughts: str = Field(description="Your thought about the question")
    action: str = Field(description="Action to take based on your thoughts")


class ReactAnswer(BaseModel):
    answer: str = Field(description="Your final answer to the question")


class Observation(BaseModel):
    observation: str = Field(description="The observation of the action")
