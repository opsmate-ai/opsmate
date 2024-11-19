from __future__ import annotations
from pydantic import BaseModel, Field
from typing_extensions import Annotated
from enum import Enum
from typing import Dict, Optional, Type, TypeVar, Iterable, List, Callable
from pydantic import ConfigDict
import yaml

T = TypeVar("T", bound=BaseModel)


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
    namespace: str = Field(title="namespace", default="default")
    labels: Dict[str, str] = Field(title="labels", default={})
    description: str = Field(title="description", default="")


class Executable(BaseModel):
    @property
    def streamable(self):
        return False

    def __call__(self, *args, **kwargs):
        raise NotImplementedError("Executable must implement __call__")

    def stream(self, *args, **kwargs):
        raise NotImplementedError("Executable can optionally implement stream")


class ContextSpec(BaseModel):
    params: Dict[str, str] = Field(title="params", default={})
    executables: list[Type[Executable]] = Field(title="executables", default=[])
    contexts: list[Context] = Field(title="contexts", default=[])
    helpers: Dict[str, Executable] = Field(
        title="helpers to provide extra contexts", default={}
    )
    data: str = Field(title="data")


class Context(BaseModel):
    metadata: Metadata = Field(title="metadata")
    spec: ContextSpec = Field(title="spec")

    def all_executables(self) -> Iterable[Type[Executable]]:
        for ctx in self.spec.contexts:
            yield from ctx.all_executables()
        yield from self.spec.executables


class TaskSpecTemplate(BaseModel):
    input: Dict[str, str] = Field(title="input", default={})
    contexts: list[Context] = Field(title="contexts", default=[])
    response_model: Type[T] = Field(title="response_model", default=BaseModel)


class TaskSpec(TaskSpecTemplate):
    instruction: str = Field(title="instruction")


class Task(BaseModel):
    metadata: Metadata = Field(title="metadata")
    spec: TaskSpec = Field(title="spec")

    @property
    def all_executables(self) -> Iterable[Type[Executable]]:
        for ctx in self.spec.contexts:
            yield from ctx.all_executables()


class TaskTemplate(BaseModel):
    metadata: Metadata = Field(title="metadata")
    spec: TaskSpecTemplate = Field(title="spec")


class BaseTaskOutput(BaseModel):
    data: str = Field(title="output of the task")


class AgentSpec(BaseModel):
    react_mode: bool = Field(
        title="react mode",
        default=False,
        description="if true, the agent will use react mode",
    )
    model: str = Field(
        title="model",
        default="gpt-4o",
        description="model to use for the agent",
    )
    max_depth: int = Field(
        title="max depth",
        default=10,
        description="max depth for the react mode",
    )
    description: str = Field(
        title="description",
        default="",
        description="description of the agent",
    )
    task_template: TaskTemplate = Field(
        title="task template",
        description="task template to use for the agent",
    )
    agents: Dict[str, Agent] = Field(
        title="agents",
        description="agents to use for the agent",
        default={},
    )


class AgentStatus(BaseModel):
    historical_context: ReactContext = Field(title="historical context", default=[])


class Agent(BaseModel):
    metadata: Metadata = Field(title="metadata")
    spec: AgentSpec = Field(title="spec")
    status: AgentStatus = Field(title="status")

    def task(self, instruction: str) -> Task:
        return Task(
            metadata=self.metadata,
            spec=TaskSpec(
                instruction=instruction,
                response_model=self.spec.task_template.spec.response_model,
                contexts=self.spec.task_template.spec.contexts,
                input=self.spec.task_template.spec.input,
            ),
        )

    # def run(self, instruction: str):
    #     raise NotImplementedError("Agent must implement run")


class ReactProcess(BaseModel):
    thought: str = Field(title="thought")
    action: str = Field(title="action")


class ReactAnswer(BaseModel):
    answer: str = Field(title="answer")


class ReactOutput(BaseModel):
    output: ReactProcess | ReactAnswer = Field(title="output")


ReactContext = List[ReactProcess | ReactAnswer]


class ExecOutput(BaseModel):
    def table_title(self):
        raise NotImplementedError("ExecOutput must implement table_title")

    def table_column_names(self):
        raise NotImplementedError("ExecOutput must implement table_column_names")

    def table_columns(self):
        return NotADirectoryError("ExecOutput must implement table_columns")


class ShellExecOutput(ExecOutput):
    command: str = Field(title="command")
    stdout: str = Field(title="stdout")
    stderr: str = Field(title="stderr")
    exit_code: int = Field(title="exit_code")

    def table_title(self):
        return "Command Execution"

    def table_column_names(self):
        return [
            ("Command", "cyan"),
            ("Stdout", "green"),
            ("Stderr", "red"),
            ("Exit Code", "magenta"),
        ]

    def table_columns(self):
        return [
            self.command,
            self.stdout,
            self.stderr,
            str(self.exit_code),
        ]


class SearchOutput(ExecOutput):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    results: list[Dict[str, str]] = Field(title="searchresults")

    def table_title(self):
        return "Search Results"

    def table_columns(self):
        return [yaml.dump(self.results) for result in self.results]

    def table_column_names(self):
        return [("Results", "cyan")]


class ExecResults(BaseModel):
    results: List[ExecOutput] = Field(title="results")

    # xxx: it's a hack
    def model_dump(self):
        return [result.model_dump() for result in self.results]


class Observation(BaseModel):
    action: str
    observation: str


class Supervisor(BaseModel):
    metadata: Metadata = Field(title="metadata")
    spec: SupervisorSpec = Field(title="spec")


AgentFactory = Callable[[str, bool, int, ReactContext, List[Context]], Agent]


class SupervisorSpec(BaseModel):
    model: str = Field(title="model", default="gpt-4o")
    max_depth: int = Field(title="max depth", default=10)
    contexts: List[Context] = Field(title="contexts")
    agents: List[Agent] = Field(title="agents")


class DocumentIngestion(BaseModel):
    metadata: Metadata = Field(title="metadata")
    spec: DocumentIngestionSpec = Field(title="spec")


class DocumentIngestionSpec(BaseModel):
    local_path: str = Field(
        title="local path",
        description="absolute path to the directory to ingest, glob patterns are supported",
    )
