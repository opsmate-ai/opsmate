from pydantic import BaseModel, Field
from enum import Enum
from typing import Dict, Optional
from instructor.client import T as InstructorT


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
    tools: list["Tool"] = Field(title="tools", default=[])
    instruction: str = Field(title="instruction")


class Context(BaseModel):
    metadata: Metadata = Field(title="metadata")
    spec: ContextSpec = Field(title="spec")


class ToolSpec(BaseModel):
    params: Dict[str, str] = Field(title="params", default={})
    contexts: list[Context] = Field(title="Tool contexts", default=[])
    instruction: str = Field(title="instruction")


class Tool(BaseModel):
    metadata: Metadata = Field(title="metadata")
    spec: ToolSpec = Field(title="spec")


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class TaskStatus(BaseModel):
    state: TaskState = Field(title="state")
    result: Optional[InstructorT] = Field(title="result", default=None)
    error: str = Field(title="error", default="")


class TaskSpec(BaseModel):
    input: Dict[str, str] = Field(title="input", default={})
    contexts: list[Context] = Field(title="Tool contexts", default=[])
    tools: list[Tool] = Field(title="tools", default=[])
    response_model: Optional[type[InstructorT]] = Field(
        title="response_model", default=str
    )
    instruction: str = Field(title="instruction")


TaskSpec.model_rebuild()


class Task(BaseModel):
    metadata: Metadata = Field(title="metadata")
    spec: TaskSpec = Field(title="spec")
    status: TaskStatus = Field(
        title="status", default_factory=lambda: TaskStatus(state=TaskState.PENDING)
    )
