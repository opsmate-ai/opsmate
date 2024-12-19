from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(description="The role of the message")
    content: str = Field(description="The content of the message")


class React(BaseModel):
    thoughts: str = Field(description="Your thought about the question")
    action: str = Field(description="Action to take based on your thoughts")


class ReactAnswer(BaseModel):
    answer: str = Field(description="Your final answer to the question")


class Observation(BaseModel):
    output: str | BaseModel = Field(description="The output of the action")
    observation: str = Field(description="The observation of the action")
