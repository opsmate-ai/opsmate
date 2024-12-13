import enum
from sqlmodel import (
    SQLModel,
    Field,
    Column,
    Enum,
    LargeBinary,
    update,
    select,
    Session,
    JSON,
    Text,
)
from opsmate.libs.providers import Client as ProviderClient
from opsmate.libs.core.engine.agent_executor import AgentExecutor, AgentCommand
from opsmate.libs.agents import supervisor_agent, k8s_agent as _k8s_agent
from datetime import datetime
from typing import List
from sqlmodel import Relationship

client_bag = ProviderClient.clients_from_env()

executor = AgentExecutor(client_bag, ask=False)

k8s_agent = _k8s_agent(
    model="gpt-4o",
    provider="openai",
    react_mode=True,
    max_depth=10,
)

# supervisor = supervisor_agent(
#     model="gpt-4o",
#     provider="openai",
#     extra_contexts="You are a helpful SRE manager who manages a team of SMEs",
#     agents=[],
# )


class CellLangEnum(enum.Enum):
    TEXT_INSTRUCTION = "text instruction"
    NOTES = "notes"
    BASH = "bash"


class WorkflowEnum(str, enum.Enum):
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"


class ThinkingSystemEnum(str, enum.Enum):
    TYPE1 = "type-1"
    TYPE2 = "type-2"


class BluePrint(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str = Field(default="")

    workflows: List["Workflow"] = Relationship(
        back_populates="blueprint", sa_relationship_kwargs={"order_by": "Workflow.id"}
    )

    @classmethod
    def find_by_id(cls, session: Session, id: int):
        return session.exec(select(cls).where(cls.id == id)).first()

    @classmethod
    def find_by_name(cls, session: Session, name: str):
        return session.exec(select(cls).where(cls.name == name)).first()

    @classmethod
    def find_workflow_by_name(cls, session: Session, name: str):
        return session.exec(
            select(Workflow)
            .where(Workflow.blueprint_id == cls.id)
            .where(Workflow.name == name)
        ).first()

    def active_workflow(self, session: Session):
        return session.exec(
            select(Workflow)
            .where(Workflow.blueprint_id == self.id)
            .where(Workflow.active == True)
        ).first()

    def activate_workflow(self, session: Session, id: int):
        # update all workflows to inactive
        session.exec(
            update(Workflow)
            .where(Workflow.blueprint_id == self.id)
            .values(active=False)
        )
        # update the workflow to active
        session.exec(
            update(Workflow)
            .where(Workflow.blueprint_id == self.id)
            .where(Workflow.id == id)
            .values(active=True)
        )
        session.commit()


class Workflow(SQLModel, table=True):
    __table_args__ = {
        "extend_existing": True,
        # "UniqueConstraint": UniqueConstraint(
        #     "name", "blueprint_id", name="unique_workflow_name_per_blueprint"
        # ),
    }

    id: int = Field(primary_key=True)
    name: str = Field(index=True)
    title: str = Field(nullable=False)
    description: str = Field(nullable=False)
    active: bool = Field(default=False)

    blueprint_id: int = Field(foreign_key="blueprint.id")
    blueprint: BluePrint = Relationship(back_populates="workflows")

    depending_workflow_ids: List[int] = Field(sa_column=Column(JSON), default=[])

    result: str = Field(
        default="",
        description="The result of the workflow execution",
        sa_column=Column(Text),
    )

    cells: List["Cell"] = Relationship(
        back_populates="workflow", sa_relationship_kwargs={"order_by": "Cell.sequence"}
    )

    @classmethod
    def find_by_id(cls, session: Session, id: int):
        return session.exec(select(cls).where(cls.id == id)).first()

    def depending_workflows(self, session: Session):
        if not self.depending_workflow_ids:
            return []
        return session.exec(
            select(Workflow).where(Workflow.id.in_(self.depending_workflow_ids))
        ).all()

    def activate_cell(self, session: Session, cell_id: int):
        # update all cells to inactive
        session.exec(
            update(Cell).where(Cell.workflow_id == self.id).values(active=False)
        )
        # update the cell to active
        session.exec(
            update(Cell)
            .where(Cell.workflow_id == self.id)
            .where(Cell.id == cell_id)
            .values(active=True)
        )
        session.commit()

    def active_cell(self, session: Session):
        return session.exec(
            select(Cell).where(Cell.workflow_id == self.id).where(Cell.active == True)
        ).first()

    def find_cell_by_name(self, session: Session, cell_name: str):
        return session.exec(
            select(Cell)
            .where(Cell.workflow_id == self.id)
            .where(Cell.name == cell_name)
        ).first()

    def find_cell_by_id(self, session: Session, cell_id: int):
        return session.exec(
            select(Cell).where(Cell.workflow_id == self.id).where(Cell.id == cell_id)
        ).first()

    def find_previous_cells(self, session: Session, cell: "Cell"):
        return session.exec(
            select(Cell)
            .where(Cell.workflow_id == self.id)
            .where(Cell.sequence < cell.sequence)
            .order_by(Cell.sequence)
        ).all()


class Cell(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    input: str = Field(default="")
    output: bytes = Field(sa_column=Column(LargeBinary))
    lang: CellLangEnum = Field(
        sa_column=Column(
            Enum(CellLangEnum),
            default=CellLangEnum.TEXT_INSTRUCTION,
            nullable=True,
            index=False,
        )
    )
    thinking_system: ThinkingSystemEnum = Field(default=ThinkingSystemEnum.TYPE1)
    sequence: int = Field(default=0)
    execution_sequence: int = Field(default=0)
    active: bool = Field(default=False)

    workflow_id: int = Field(foreign_key="workflow.id")
    workflow: Workflow = Relationship(back_populates="cells")

    hidden: bool = Field(default=False)

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def find_by_id(cls, session: Session, id: int):
        return session.exec(select(cls).where(cls.id == id)).first()


class KVStore(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    key: str = Field(unique=True, index=True)
    value: JSON = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default=datetime.now())
    updated_at: datetime = Field(default=datetime.now())

    class Config:
        arbitrary_types_allowed = True


def default_new_cell(workflow: Workflow):
    if workflow.blueprint.name == "polya":
        thinking_system = ThinkingSystemEnum.TYPE2
    else:
        thinking_system = ThinkingSystemEnum.TYPE1

    return Cell(
        input="",
        active=True,
        workflow_id=workflow.id,
        thinking_system=thinking_system,
    )
