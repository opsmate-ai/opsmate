from opsmate.gui.seed import seed_blueprints
from opsmate.gui.models import BluePrint, default_new_cell, ThinkingSystemEnum, SQLModel
from sqlmodel import Session, create_engine
from sqlalchemy import Engine
import pytest


@pytest.fixture
def engine():
    engine = create_engine("sqlite:///:memory:", echo=True)
    return engine


@pytest.fixture
def session(engine: Engine):
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_seed_polya_blueprints(session: Session):
    seed_blueprints(session)

    polya = BluePrint.find_by_name(session, "polya")
    assert polya is not None
    assert polya.name == "polya"
    assert polya.description == "Polya's method for problem solving"

    workflows = polya.workflows
    assert len(workflows) == 4

    assert workflows[0].name == "understanding"
    assert workflows[0].title == "1. Understanding"
    assert workflows[0].description.startswith(
        "\nLet's understand the problem together:"
    )
    assert workflows[0].active is True
    assert workflows[0].depending_workflow_ids == []
    assert workflows[0].depending_workflows(session) == []

    assert workflows[1].name == "planning"
    assert workflows[1].title == "2. Planning"
    assert workflows[1].description.startswith(
        "\nNow that we understand the problem, let's develop a strategy:"
    )
    assert workflows[1].active is False
    assert workflows[1].depending_workflow_ids == [workflows[0].id]
    assert workflows[1].depending_workflows(session) == [workflows[0]]

    assert workflows[2].name == "execution"
    assert workflows[2].title == "3. Execution"
    assert workflows[2].description.startswith(
        "\nLet's execute our plan stage by stage:"
    )
    assert workflows[2].active is False
    assert workflows[2].depending_workflow_ids == [workflows[1].id]
    assert workflows[2].depending_workflows(session) == [workflows[1]]

    assert workflows[3].name == "review"
    assert workflows[3].title == "4. Looking Back"
    assert workflows[3].description.startswith("\nLet's reflect on our solution:")
    assert workflows[3].active is False
    assert workflows[3].depending_workflow_ids == [workflows[2].id]
    assert workflows[3].depending_workflows(session) == [workflows[2]]


def test_seed_freestyle_blueprints(session: Session):
    seed_blueprints(session)

    freestyle = BluePrint.find_by_name(session, "freestyle")
    assert freestyle is not None
    assert freestyle.name == "freestyle"
    assert freestyle.description == "Freestyle problem solving"

    workflows = freestyle.workflows
    assert len(workflows) == 1
    assert workflows[0].name == "freestyle"
    assert workflows[0].title == "Freestyle"
    assert workflows[0].description == "Freestyle problem solving"
    assert workflows[0].active is True
    assert workflows[0].depending_workflow_ids == []
    assert workflows[0].depending_workflows(session) == []


def test_default_new_cell(session: Session):
    seed_blueprints(session)
    freestyle = BluePrint.find_by_name(session, "freestyle")
    assert freestyle is not None

    cell = default_new_cell(freestyle.workflows[0])
    assert cell is not None
    assert cell.input == ""
    assert cell.active is True
    assert cell.workflow_id == freestyle.workflows[0].id
    assert cell.thinking_system == ThinkingSystemEnum.REASONING


def test_default_new_cell_polya(session: Session):
    seed_blueprints(session)
    polya = BluePrint.find_by_name(session, "polya")
    assert polya is not None

    cell = default_new_cell(polya.workflows[0])
    assert cell is not None
    assert cell.input == ""
    assert cell.active is True
    assert cell.workflow_id == polya.workflows[0].id
    assert cell.thinking_system == ThinkingSystemEnum.TYPE2


def test_activate_workflow(session: Session):
    seed_blueprints(session)
    polya = BluePrint.find_by_name(session, "polya")
    assert polya is not None

    polya.activate_workflow(session, polya.workflows[1].id)

    session.refresh(polya)
    assert polya.workflows[0].active is False
    assert polya.workflows[1].active is True
    assert polya.workflows[2].active is False
    assert polya.workflows[3].active is False


def test_activate_cell(session: Session):
    seed_blueprints(session)
    polya = BluePrint.find_by_name(session, "polya")
    workflow = polya.workflows[0]

    for i in range(4):
        cell = default_new_cell(workflow)
        if i == 0:
            cell.active = True
        else:
            cell.active = False
        session.add(cell)
        session.commit()

    workflow.activate_cell(session, workflow.cells[1].id)
    session.refresh(workflow)

    assert workflow.cells[0].active is False
    assert workflow.cells[1].active is True
    assert workflow.cells[2].active is False
    assert workflow.cells[3].active is False
