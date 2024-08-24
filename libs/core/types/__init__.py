from __future__ import annotations
from pydantic import BaseModel, Field
from typing_extensions import Annotated
from enum import Enum
from typing import Dict, Optional, Type, TypeVar, Iterable, Callable


T = TypeVar("T", bound=BaseModel)

ToolCallable = Callable[..., BaseModel]


class CapabilityType(str, Enum):
    LIST = "system:list"
    FIND = "system:find"
    DELETE = "system:delete"
    READ = "system:read"
    WRITE = "system:write"
    APPEND = "system:append"
    GETENV = "system:getenv"
    EXECUTE = "system:execute"
    TIME = "system:time"
    SIGNAL = "system:signal"


class Metadata(BaseModel):
    name: str = Field(title="name")
    apiVersion: str = Field(title="apiVersion")
    labels: Dict[str, str] = Field(title="labels", default={})
    description: str = Field(title="description", default="")


class ContextSpec(BaseModel):
    params: Dict[str, str] = Field(title="params", default={})
    executables: list[Callable] = Field(title="executables", default=[])
    contexts: list[Context] = Field(title="contexts", default=[])
    data: str = Field(title="data")


class Context(BaseModel):
    metadata: Metadata = Field(title="metadata")
    spec: ContextSpec = Field(title="spec")

    def all_executables(self) -> Iterable[ToolCallable]:
        for ctx in self.spec.contexts:
            yield from ctx.all_executables()
        yield from self.spec.executables


# class TaskState(str, Enum):
#     PENDING = "pending"
#     RUNNING = "running"
#     SUCCESS = "success"
#     FAILED = "failed"


# class TaskStatus(BaseModel):
#     state: TaskState = Field(title="state")
#     result: Optional[T] = Field(title="result", default=None)
#     error: str = Field(title="error", default="")


class TaskSpec(BaseModel):
    input: Dict[str, str] = Field(title="input", default={})
    contexts: list[Context] = Field(title="contexts", default=[])
    response_model: Type[T] = Field(title="response_model", default=BaseModel)
    instruction: str = Field(title="instruction")


class Task(BaseModel):
    metadata: Metadata = Field(title="metadata")
    spec: TaskSpec = Field(title="spec")
    # status: TaskStatus = Field(
    #     title="status", default_factory=lambda: TaskStatus(state=TaskState.PENDING)
    # )


class BaseTaskOutput(BaseModel):
    data: str = Field(title="output of the task")


class ReactOutput(BaseModel):
    # question: Annotated[Optional[str], Field(default=None)]
    thought: Annotated[Optional[str], Field(default=None)]
    # actions: Annotated[Optional[str], Field(default=None)]
    observation: Annotated[Optional[str], Field(default=None)]
    answer: Annotated[Optional[str], Field(default=None)]
