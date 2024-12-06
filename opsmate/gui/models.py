import enum
import sqlmodel
from opsmate.libs.providers import Client as ProviderClient
from opsmate.libs.core.engine.agent_executor import AgentExecutor, AgentCommand
from opsmate.libs.agents import supervisor_agent, k8s_agent as _k8s_agent

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


class CellEnum(enum.Enum):
    TEXT_INSTRUCTION = "text instruction"
    BASH = "bash"


class StageEnum(str, enum.Enum):
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"


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
    },
]


def get_active_stage():
    stage = next(stage for stage in stages if stage["active"])
    if stage is None:
        return stages[0]
    return stage


class Cell(sqlmodel.SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: int = sqlmodel.Field(primary_key=True)
    input: str = sqlmodel.Field(default="")
    # output: dict = sqlmodel.Field(sa_column=sqlmodel.Column(sqlmodel.JSON))
    output: bytes = sqlmodel.Field(sa_column=sqlmodel.Column(sqlmodel.LargeBinary))
    type: CellEnum = sqlmodel.Field(
        sa_column=sqlmodel.Column(
            sqlmodel.Enum(CellEnum),
            default=CellEnum.TEXT_INSTRUCTION,
            nullable=True,
            index=False,
        )
    )
    sequence: int = sqlmodel.Field(default=0)
    execution_sequence: int = sqlmodel.Field(default=0)
    active: bool = sqlmodel.Field(default=False)
    stage: StageEnum = sqlmodel.Field(default=StageEnum.UNDERSTANDING)

    class Config:
        arbitrary_types_allowed = True


async def mark_cell_inactive(stage: StageEnum, session: sqlmodel.Session):
    # update all cells to inactive
    session.exec(sqlmodel.update(Cell).where(Cell.stage == stage).values(active=False))
    session.commit()


async def mark_cell_active(cell_id: int, session: sqlmodel.Session):
    session.exec(sqlmodel.update(Cell).where(Cell.id == cell_id).values(active=True))
    session.commit()


async def all_cells_ordered(stage: StageEnum, session: sqlmodel.Session):
    return session.exec(
        sqlmodel.select(Cell).where(Cell.stage == stage).order_by(Cell.sequence)
    ).all()


async def find_cell_by_id(cell_id: int, session: sqlmodel.Session):
    return session.exec(sqlmodel.select(Cell).where(Cell.id == cell_id)).first()
