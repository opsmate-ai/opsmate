import pickle

import pytest
from pydantic import BaseModel

from opsmate.gui.models import (
    Cell,
    Workflow,
    SQLModel,
    conversation_context,
    normalize_output_format,
)
from sqlmodel import create_engine, Session


@pytest.fixture(scope="module")
def engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


# Fixture to provide a new session for each test
@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


class DemoModel(BaseModel):
    a: str
    b: int


def test_normalize_output_format():
    assert normalize_output_format(DemoModel(a="b", b=1)) == {
        "a": "b",
        "b": 1,
    }
    assert normalize_output_format("abc") == "abc"
    assert normalize_output_format(1) == 1
    assert normalize_output_format(1.0) == 1.0

    assert normalize_output_format([DemoModel(a="b", b=1), {"c": "d", "e": 2.0}]) == [
        {"a": "b", "b": 1},
        {"c": "d", "e": 2.0},
    ]

    assert normalize_output_format(
        {
            "a": DemoModel(a="b", b=1),
            "b": {"c": "d", "e": 2.0},
            "c": [DemoModel(a="b", b=1), {"c": "d", "e": 2.0}],
        }
    ) == {
        "a": {"a": "b", "b": 1},
        "b": {"c": "d", "e": 2.0},
        "c": [{"a": "b", "b": 1}, {"c": "d", "e": 2.0}],
    }


def test_conversation_context(session):
    # Create a workflow and add it to the session
    workflow = Workflow(
        name="Test Workflow",
        title="Test Workflow",
        description="Test Workflow",
        active=True,
        blueprint_id=1,
    )
    session.add(workflow)
    session.commit()

    # Create previous cells with inputs and outputs
    previous_cell_1 = Cell(
        input="User input 1",
        output=pickle.dumps(
            [
                {"output": {"key": "value"}},
                {"output": {"key2": "value2"}},
            ]
        ),
        workflow_id=workflow.id,
        sequence=1,
        execution_sequence=1,
        active=True,
    )

    previous_cell_2 = Cell(
        input="User input 2",
        output=pickle.dumps([{"output": "Assistant output 2"}]),
        workflow_id=workflow.id,
        sequence=2,
        execution_sequence=2,
        active=True,
    )

    # Add cells to the session
    session.add(previous_cell_1)
    session.add(previous_cell_2)
    session.commit()

    # Create a new cell to test
    cell = Cell(
        workflow_id=workflow.id,
        sequence=3,
        execution_sequence=3,
        active=True,
    )
    session.add(cell)
    session.commit()

    # Execute the function
    conversations = list(conversation_context(cell, session))

    # Assertions
    print(conversations)
    assert len(conversations) == 2

    assert (
        conversations[0]
        == """
Conversation 1:

<user instruction>
User input 1
</user instruction>

<assistant response>
key: value
---
key2: value2

</assistant response>
"""
    )

    assert (
        conversations[1]
        == """
Conversation 2:

<user instruction>
User input 2
</user instruction>

<assistant response>
Assistant output 2
</assistant response>
"""
    )
