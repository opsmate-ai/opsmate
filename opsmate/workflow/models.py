from sqlmodel import SQLModel, Field, Column, JSON, LargeBinary, Relationship
from datetime import datetime
from typing import List
from enum import Enum
import sqlalchemy as sa
from collections import defaultdict, deque
from sqlmodel import Session


class WorkflowType(Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    NONE = "none"


class WorkflowState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Workflow(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    description: str
    steps: List["WorkflowStep"] = Relationship(back_populates="workflow")

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
    workflow_id: int = Field(foreign_key="workflow.id", index=True)
    workflow: Workflow = Relationship(back_populates="steps")
    prev_ids: List[int] = Field(sa_column=Column(JSON))
    result: bytes = Field(sa_column=Column(LargeBinary), default=b"")
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

    def prev_steps(self, session: Session):
        return [session.get(WorkflowStep, prev_id) for prev_id in self.prev_ids]
