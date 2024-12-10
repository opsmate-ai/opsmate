import enum
from sqlmodel import (
    SQLModel,
    Field,
    Column,
    Enum,
    LargeBinary,
    insert,
    update,
    select,
    Session,
    JSON,
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

supervisor = supervisor_agent(
    model="gpt-4o",
    provider="openai",
    extra_contexts="You are a helpful SRE manager who manages a team of SMEs",
    agents=[],
)


class CellLangEnum(enum.Enum):
    TEXT_INSTRUCTION = "text instruction"
    BASH = "bash"


class StageEnum(str, enum.Enum):
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

    def depending_workflows(self, session: Session):
        if not self.depending_workflow_ids:
            return []
        return session.exec(
            select(Workflow).where(Workflow.id.in_(self.depending_workflow_ids))
        ).all()


stages = [
    {
        "id": StageEnum.UNDERSTANDING.value,
        "title": "1. Understanding",
        "description": """
Let's understand the problem together:

1. What exactly is unknown or what are we trying to find?
2. What data or information do we have?
3. What are the conditions or constraints?
4. Can you draw or visualize any part of this problem?

Please share your thoughts on these points.
        """,
        "active": True,
        "workflow": True,
    },
    {
        "id": StageEnum.PLANNING.value,
        "title": "2. Planning",
        "description": """
Now that we understand the problem, let's develop a strategy:

1. Have you seen similar problems before?
2. Can we break this into smaller sub-problems?
3. What mathematical techniques might be relevant?
4. Should we try solving a simpler version first?

Share your thoughts on possible approaches.
        """,
        "active": False,
        "workflow": True,
    },
    {
        "id": StageEnum.EXECUTION.value,
        "title": "3. Execution",
        "description": """
Let's execute our plan stage by stage:

1. Write out each stage clearly
2. Verify each stage as you go
3. Keep track of your progress
4. Note any obstacles or insights

Begin implementing your solution below.
        """,
        "active": False,
        "workflow": True,
    },
    {
        "id": StageEnum.REVIEW.value,
        "title": "4. Looking Back",
        "description": """
Let's reflect on our solution:

1. Does the answer make sense?
2. Can we verify the result?
3. Is there a simpler way?
4. What did we learn from this?

Share your reflections below.
        """,
        "active": False,
        "workflow": True,
    },
]


class KVStore(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    key: str = Field(unique=True, index=True)
    value: JSON = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default=datetime.now())
    updated_at: datetime = Field(default=datetime.now())

    class Config:
        arbitrary_types_allowed = True


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
    stage: StageEnum = Field(default=StageEnum.UNDERSTANDING)

    class Config:
        arbitrary_types_allowed = True


class Stages:
    @classmethod
    def init_stages_in_kvstore(cls, session: Session):
        session.exec(insert(KVStore).values(key="stages", value=stages))
        session.commit()

    @classmethod
    def all_workflow_based(cls, session: Session):
        """
        Get all workflow based stages from kvstore
        """
        stages = session.exec(select(KVStore).where(KVStore.key == "stages")).first()
        return [stage for stage in stages.value if stage.get("workflow")]

    @classmethod
    def active(cls, session: Session):
        stages = cls.all_workflow_based(session)
        stage = next(stage for stage in stages if stage["active"])
        if stage is None:
            return stages[0]
        return stage

    @classmethod
    def save(cls, session: Session, stages: dict):
        session.exec(
            update(KVStore).where(KVStore.key == "stages").values(value=stages)
        )
        session.commit()

    @classmethod
    def get(cls, session: Session, stage_id: str):
        stages = cls.all_workflow_based(session)
        return next((stage for stage in stages if stage["id"] == stage_id), None)

    @classmethod
    def activate(cls, session: Session, stage_id: str):
        stages = cls.all_workflow_based(session)
        for stage in stages:
            stage["active"] = False
        for stage in stages:
            if stage["id"] == stage_id:
                stage["active"] = True
        cls.save(session, stages)


async def mark_cell_inactive(stage: StageEnum, session: Session):
    # update all cells to inactive
    session.exec(update(Cell).where(Cell.stage == stage).values(active=False))
    session.commit()


async def mark_cell_active(cell_id: int, session: Session):
    session.exec(update(Cell).where(Cell.id == cell_id).values(active=True))
    session.commit()


async def all_cells_ordered(stage: StageEnum, session: Session):
    return session.exec(
        select(Cell).where(Cell.stage == stage).order_by(Cell.sequence)
    ).all()


async def find_cell_by_id(cell_id: int, session: Session):
    return session.exec(select(Cell).where(Cell.id == cell_id)).first()


def default_new_cell(stage: dict):
    if stage.get("workflow"):
        thinking_system = ThinkingSystemEnum.TYPE2
    else:
        thinking_system = ThinkingSystemEnum.TYPE1

    return Cell(
        input="",
        active=True,
        stage=stage["id"],
        thinking_system=thinking_system,
    )
