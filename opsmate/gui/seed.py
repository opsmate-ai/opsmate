from sqlmodel import Session, select, create_engine
from opsmate.gui.models import BluePrint, Workflow, WorkflowEnum, default_new_cell
from opsmate.config import config

polya_workflows = [
    {
        "name": WorkflowEnum.UNDERSTANDING.value,
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
        "name": WorkflowEnum.PLANNING.value,
        "title": "2. Planning",
        "description": """
Now that we understand the problem, let's develop a strategy:

1. Have you seen similar problems before?
2. Can we break this into smaller sub-problems?
3. Should we try solving a simpler version first?

Share your thoughts on possible approaches.
        """,
        "active": False,
    },
    {
        "name": WorkflowEnum.EXECUTION.value,
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
        "name": WorkflowEnum.REVIEW.value,
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


freestyle_workflows = [
    {
        "name": WorkflowEnum.FREESTYLE.value,
        "title": "Freestyle",
        "description": "Freestyle problem solving",
        "active": True,
    },
]


def polya_blueprint(session: Session):
    # find the blueprint
    blueprint = session.exec(select(BluePrint).where(BluePrint.name == "polya")).first()
    if blueprint:
        return blueprint

    blueprint = BluePrint(
        name="polya",
        description="Polya's method for problem solving",
    )
    session.add(blueprint)
    session.commit()
    add_polya_workflows(session, blueprint)

    return blueprint


def freestyle_blueprint(session: Session):
    blueprint = session.exec(
        select(BluePrint).where(BluePrint.name == WorkflowEnum.FREESTYLE.value)
    ).first()
    if blueprint:
        return blueprint

    blueprint = BluePrint(
        name="freestyle",
        description="Freestyle problem solving",
    )
    session.add(blueprint)
    session.commit()
    add_freestyle_workflows(session, blueprint)
    return blueprint


def add_freestyle_workflows(session: Session, freestyle: BluePrint):
    # add the workflows
    prev_workflow_id = None
    for idx, workflow in enumerate(freestyle_workflows):
        workflow = Workflow(
            name=workflow["name"],
            title=workflow["title"],
            description=workflow["description"],
            active=workflow["active"],
            blueprint_id=freestyle.id,
            depending_workflow_ids=[prev_workflow_id] if prev_workflow_id else [],
        )
        session.add(workflow)
        session.commit()
        prev_workflow_id = workflow.id

    return freestyle


def add_polya_workflows(session: Session, polya: BluePrint):
    # add the workflows
    prev_workflow_id = None
    for idx, workflow in enumerate(polya_workflows):
        workflow = Workflow(
            name=workflow["name"],
            title=workflow["title"],
            description=workflow["description"],
            active=workflow["active"],
            blueprint_id=polya.id,
            depending_workflow_ids=[prev_workflow_id] if prev_workflow_id else [],
        )
        session.add(workflow)
        session.commit()
        prev_workflow_id = workflow.id


def seed_blueprints(session: Session):
    polya_blueprint(session)
    freestyle_blueprint(session)

    blueprints = session.exec(select(BluePrint)).all()
    for blueprint in blueprints:
        for workflow in blueprint.workflows:
            if len(workflow.cells) == 0:
                new_cell = default_new_cell(workflow)
                if workflow.name == WorkflowEnum.PLANNING:
                    new_cell.input = "can you solve the problem based on the context?"
                session.add(new_cell)
                session.commit()
