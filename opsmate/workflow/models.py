from sqlmodel import (
    SQLModel as _SQLModel,
    Field,
    Column,
    JSON,
    LargeBinary,
    Relationship,
    MetaData,
)
from datetime import datetime
from typing import List
from enum import Enum
import sqlalchemy as sa
from collections import defaultdict, deque
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy.orm import registry
from typing import Dict, Any
import pickle
import importlib


class SQLModel(_SQLModel, registry=registry()):
    metadata = MetaData()


class WorkflowType(Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    NONE = "none"
    COND_TRUE = "cond_true"
    COND_FALSE = "cond_false"


class WorkflowState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowFailedReason(Enum):
    PREV_STEP_FAILED = "prev_step_failed"
    RUNTIME_ERROR = "runtime_error"
    NONE = "none"


class Workflow(SQLModel, table=True):
    __tablename__ = "opsmate_workflow"
    id: int = Field(primary_key=True)
    name: str
    description: str
    steps: List["WorkflowStep"] = Relationship(back_populates="workflow")
    state: WorkflowState = Field(default=WorkflowState.PENDING)

    created_at: datetime | None = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
        sa_column_kwargs={"server_default": sa.func.now()},
        nullable=False,
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
        sa_column_kwargs={"onupdate": sa.func.now(), "server_default": sa.func.now()},
    )

    def runnable_steps(self, session: Session):
        return [step for step in self.steps if step.runnable(session)]

    def find_step(self, fn_name: str, session: Session, metadata: Dict[str, Any] = {}):
        stmt = (
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == self.id)
            .where(WorkflowStep.name == fn_name)
        )
        if metadata:
            out = session.exec(stmt).all()
            for step in out:
                matches = True
                for key, value in metadata.items():
                    if step.meta.get(key) != value:
                        matches = False
                        break
                if matches:
                    return step
            return None
        return session.exec(stmt).first()

    def topological_sort(self, session: Session):
        nodes = {}
        edges = defaultdict(list)

        def build(node: WorkflowStep):
            node_id = node.id
            if node_id not in nodes:
                nodes[node_id] = node
                for child in node.prev_steps(session):
                    build(child)
                    # points from child to parent for the purpose of topological sort
                    edges[child.id].append(node_id)

        for workflow_step in self.steps:
            build(workflow_step)

        visited = set()
        stack = deque()

        def visit(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)

            for parent_id in edges[node_id]:
                if parent_id not in visited:
                    visit(parent_id)
            stack.appendleft(node_id)

        for node_id in nodes:
            if node_id not in visited:
                visit(node_id)

        nodes = [nodes[node_id] for node_id in stack]
        return nodes


class WorkflowStep(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str = Field(default="")
    fn: str = Field(default="")
    step_type: WorkflowType = Field(default=WorkflowType.SEQUENTIAL)
    workflow_id: int = Field(foreign_key="opsmate_workflow.id", index=True)
    workflow: Workflow = Relationship(back_populates="steps")
    prev_ids: List[int] = Field(sa_column=Column(JSON))
    marshalled_result: bytes = Field(sa_column=Column(LargeBinary), default=b"")
    marshalled_metadata: bytes = Field(sa_column=Column(LargeBinary), default=b"")
    error: str = Field(default="")
    failed_reason: WorkflowFailedReason = Field(default=WorkflowFailedReason.NONE)
    state: WorkflowState = Field(default=WorkflowState.PENDING)
    created_at: datetime | None = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
        sa_column_kwargs={"server_default": sa.func.now()},
        nullable=False,
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
        sa_column_kwargs={"onupdate": sa.func.now(), "server_default": sa.func.now()},
    )

    # getter and setter for result
    @property
    def result(self):
        return pickle.loads(self.marshalled_result)

    @result.setter
    def result(self, value):
        # to deal with instructor monkey patching
        # we need to remove the _raw_response field from the value
        # it is done via re-importing the class and creating a new instance of it
        value = self._recursive_remove_raw_response(value)
        self.marshalled_result = pickle.dumps(value)

    def _recursive_remove_raw_response(self, value):
        if isinstance(value, BaseModel):
            value = self._remove_raw_response(value)
        elif isinstance(value, dict):
            for key, val in value.items():
                value[key] = self._recursive_remove_raw_response(val)
        elif isinstance(value, list):
            for i, val in enumerate(value):
                value[i] = self._recursive_remove_raw_response(val)
        elif isinstance(value, tuple):
            value = tuple(self._recursive_remove_raw_response(val) for val in value)
        return value

    def _remove_raw_response(self, value: BaseModel):
        if hasattr(value, "_raw_response") and isinstance(value, BaseModel):
            cls = value.__class__
            # re import the class
            module_name = cls.__module__
            class_name = cls.__name__
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
            value = cls(**value.model_dump())
        return value

    # xxx: metadata is a keyword thus we use meta instead
    @property
    def meta(self):
        if self.marshalled_metadata == b"":
            return {}
        return pickle.loads(self.marshalled_metadata)

    @meta.setter
    def meta(self, value):
        self.marshalled_metadata = pickle.dumps(value)

    def prev_steps(self, session: Session):
        return [session.get(WorkflowStep, prev_id) for prev_id in self.prev_ids]

    def finished(self):
        return (
            self.state == WorkflowState.COMPLETED
            or self.state == WorkflowState.FAILED
            or self.state == WorkflowState.SKIPPED
        )

    # @classmethod
    # def find_step_by_name(cls, session: Session, name: str, workflow_id: int):
    #     stmt = select(cls).where(cls.name == name).where(cls.workflow_id == workflow_id)
    #     return session.exec(stmt).first()

    def runnable(self, session: Session):
        if self.state != WorkflowState.PENDING:
            return False
        for prev_step in self.prev_steps(session):
            if not prev_step.finished():
                return False
        return True
