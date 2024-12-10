import structlog
from pydantic import Field
from pydantic_settings import BaseSettings
import sqlmodel
from fasthtml.common import *
from opsmate.gui.models import (
    Cell,
    CellLangEnum,
    ThinkingSystemEnum,
    BluePrint,
    Workflow,
    default_new_cell,
)
from opsmate.gui.seed import seed_blueprints
from opsmate.gui.views import (
    tlink,
    dlink,
    picolink,
    nav,
    reset_button,
    add_cell_button,
    render_cell_container,
    render_workflow_panel,
    execute_llm_react_instruction,
    execute_llm_type2_instruction,
    execute_bash_instruction,
    home_body,
)

logger = structlog.get_logger()


class Config(BaseSettings):
    db_url: str = Field(default="sqlite:///:memory:", alias="OPSMATE_DB_URL")
    session_name: str = Field(default="session", alias="OPSMATE_SESSION_NAME")
    token: str = Field(default="", alias="OPSMATE_TOKEN")


config = Config()


# start a sqlite database
engine = sqlmodel.create_engine(
    config.db_url, connect_args={"check_same_thread": False}
)


def on_startup():
    sqlmodel.SQLModel.metadata.create_all(engine)


def before(req, session):
    if config.token == "":
        session["token"] = ""
        return
    if req.query_params.get("token") is not None:
        session["token"] = req.query_params.get("token", "")

    if session.get("token", "") != config.token:
        return Response("unauthorized", status_code=401)


bware = Beforeware(before)

app = FastHTML(
    hdrs=(MarkdownJS(), tlink, dlink, picolink, nav), exts="ws", before=bware
)


@app.on_event("startup")
async def startup():
    on_startup()

    # Add init cell if none exist
    with sqlmodel.Session(engine) as session:
        seed_blueprints(session)
        session.commit()

        blueprints = session.exec(sqlmodel.select(BluePrint)).all()
        for blueprint in blueprints:
            for workflow in blueprint.workflows:
                if len(workflow.cells) == 0:
                    new_cell = default_new_cell(workflow)
                    session.add(new_cell)
                    session.commit()


@app.route("/")
async def get():
    with sqlmodel.Session(engine) as session:
        blueprint = BluePrint.find_by_name(session, "polya")
        page = home_body(session, config.session_name, blueprint)
        return Title(f"{config.session_name}"), page


@app.route("/blueprint/freestyle")
async def get():
    with sqlmodel.Session(engine) as session:
        blueprint = BluePrint.find_by_name(session, "freestyle")
        page = home_body(session, config.session_name, blueprint)
        return Title(f"{config.session_name}"), page


@app.route("/blueprint/{blueprint_id}/cell/bottom")
async def post(blueprint_id: int):
    with sqlmodel.Session(engine) as session:
        blueprint = BluePrint.find_by_id(session, blueprint_id)
        active_workflow = blueprint.active_workflow(session)
        cells = active_workflow.cells

        # get the highest sequence number
        max_sequence = max(cell.sequence for cell in cells) if cells else 0
        # get the higest execution sequence number
        max_execution_sequence = (
            max(cell.execution_sequence for cell in cells) if cells else 0
        )
        new_cell = default_new_cell(active_workflow)
        new_cell.sequence = max_sequence + 1
        new_cell.execution_sequence = max_execution_sequence + 1

        session.add(new_cell)
        session.commit()

        active_workflow.activate_cell(session, new_cell.id)

        session.refresh(active_workflow)
        cells = active_workflow.cells
        return (
            # Return the new cell to be added
            render_cell_container(cells, hx_swap_oob="true"),
            # Return the button to preserve it
            add_cell_button(blueprint),
        )


# Add cell manipulation routes
@app.route("/blueprint/{blueprint_id}/cell/{cell_id}")
async def post(
    blueprint_id: int,
    cell_id: int,
    above: bool = False,
    session: sqlmodel.Session = None,
):
    with sqlmodel.Session(engine) as session:
        blueprint = BluePrint.find_by_id(session, blueprint_id)
        active_workflow = blueprint.active_workflow(session)
        selected_cell = active_workflow.find_cell_by_id(session, cell_id)
        cells = active_workflow.cells

        new_cell = default_new_cell(active_workflow)

        # get the highest execution sequence number
        max_execution_sequence = (
            max(cell.execution_sequence for cell in cells) if cells else 0
        )
        new_cell.execution_sequence = max_execution_sequence + 1

        # get the current sequence number

        if above:
            new_cell.sequence = selected_cell.sequence
        else:
            new_cell.sequence = selected_cell.sequence + 1

        session.add(new_cell)
        # find all cells with a sequence greater than the current cell
        cells_to_shift = [
            cell for cell in cells if cell.sequence >= selected_cell.sequence
        ]
        for cell in cells_to_shift:
            cell.sequence += 1
            session.add(cell)
        session.commit()

        # reload the cells
        active_workflow.activate_cell(session, new_cell.id)
        session.refresh(active_workflow)
        cells = active_workflow.cells
        return render_cell_container(cells, hx_swap_oob="true")


@app.route("/blueprint/{blueprint_id}/cell/{cell_id}")
async def delete(blueprint_id: int, cell_id: int):
    with sqlmodel.Session(engine) as session:
        blueprint = BluePrint.find_by_id(session, blueprint_id)
        active_workflow = blueprint.active_workflow(session)
        selected_cell = active_workflow.find_cell_by_id(session, cell_id)

        if selected_cell is None:
            return ""

        # find all cells with a sequence greater than the current cell
        cells_to_shift = session.exec(
            sqlmodel.select(Cell)
            .where(Cell.workflow_id == active_workflow.id)
            .where(Cell.sequence > selected_cell.sequence)
        ).all()
        for cell in cells_to_shift:
            cell.sequence -= 1
            session.add(cell)

        session.delete(selected_cell)
        session.commit()

        session.refresh(active_workflow)
        cells = active_workflow.cells

        return render_cell_container(cells, hx_swap_oob="true")


@app.route("/blueprint/{blueprint_id}/cell/{cell_id}")
async def put(
    blueprint_id: int,
    cell_id: int,
    input: str = None,
    lang: str = None,
    thinking_system: str = None,
):
    logger.info(
        "updating cell",
        cell_id=cell_id,
        input=input,
        lang=lang,
        thinking_system=thinking_system,
    )

    with sqlmodel.Session(engine) as session:
        blueprint = BluePrint.find_by_id(session, blueprint_id)
        active_workflow = blueprint.active_workflow(session)
        selected_cell = active_workflow.find_cell_by_id(session, cell_id)
        if selected_cell is None:
            return ""

        selected_cell.active = True
        if input is not None:
            selected_cell.input = input
        if lang is not None:
            if lang == CellLangEnum.TEXT_INSTRUCTION.value:
                selected_cell.lang = CellLangEnum.TEXT_INSTRUCTION
            elif lang == CellLangEnum.BASH.value:
                selected_cell.lang = CellLangEnum.BASH

        if thinking_system is not None:
            if thinking_system == ThinkingSystemEnum.TYPE1.value:
                logger.info("setting thinking system to type 1")
                selected_cell.thinking_system = ThinkingSystemEnum.TYPE1
            elif thinking_system == ThinkingSystemEnum.TYPE2.value:
                logger.info("setting thinking system to type 2")
                selected_cell.thinking_system = ThinkingSystemEnum.TYPE2

        session.add(selected_cell)
        session.commit()

        active_workflow.activate_cell(session, selected_cell.id)

        session.refresh(active_workflow)
        cells = active_workflow.cells

        return render_cell_container(cells, hx_swap_oob="true")


@app.route("/blueprint/{blueprint_id}/cell/input/{cell_id}")
async def put(blueprint_id: int, cell_id: int, input: str):
    with sqlmodel.Session(engine) as session:
        blueprint = BluePrint.find_by_id(session, blueprint_id)
        active_workflow = blueprint.active_workflow(session)
        selected_cell = active_workflow.find_cell_by_id(session, cell_id)

        if selected_cell is None:
            return ""

        selected_cell.input = input
        selected_cell.active = True
        session.add(selected_cell)
        session.commit()

        active_workflow.activate_cell(session, selected_cell.id)
        return ""


@app.route("/workflow/{workflow_id}/switch")
async def put(workflow_id: str):
    logger.info("switching workflow", workflow_id=workflow_id)

    with sqlmodel.Session(engine) as session:
        workflow = Workflow.find_by_id(session, workflow_id)
        blueprint = workflow.blueprint
        blueprint.activate_workflow(session, workflow_id)

        session.refresh(blueprint)
        active_workflow = blueprint.active_workflow(session)

        return (
            render_workflow_panel(blueprint.workflows, active_workflow),
            render_cell_container(active_workflow.cells, hx_swap_oob="true"),
        )


@app.route("/blueprint/{blueprint_id}/cells/reset")
async def post(blueprint_id: int):
    with sqlmodel.Session(engine) as session:
        blueprint = BluePrint.find_by_id(session, blueprint_id)
        active_workflow = blueprint.active_workflow(session)
        session.exec(
            sqlmodel.delete(Cell).where(Cell.workflow_id == active_workflow.id)
        )
        session.commit()

        # create new cells
        new_cell = default_new_cell(active_workflow)
        session.add(new_cell)
        session.commit()

        session.refresh(active_workflow)
        session.refresh(new_cell)
        return (
            render_cell_container(active_workflow.cells, hx_swap_oob="true"),
            reset_button(blueprint),
        )


@app.ws("/cell/run/ws/")
async def ws(cell_id: int, input: str, send, session):
    logger.info("running cell", cell_id=cell_id, input=input)
    # Check authentication token
    if session.get("token", "") != config.token:
        logger.error("unauthorized", token=session.get("token"))
        return  # Exit if unauthorized

    with sqlmodel.Session(engine) as session:
        cell = Cell.find_by_id(session, cell_id)
        active_workflow = cell.workflow
        active_workflow.activate_cell(session, cell_id)

        cell = session.exec(sqlmodel.select(Cell).where(Cell.id == cell_id)).first()
        logger.info(
            "selected cell",
            cell_id=cell_id,
            input=cell.input,
            cell_lang=cell.lang,
        )
        cell.active = True
        session.add(cell)
        session.commit()

        if cell is None:
            logger.error("cell not found", cell_id=cell_id)
            return

        swap = "beforeend"
        if cell.lang == CellLangEnum.TEXT_INSTRUCTION:
            if cell.thinking_system == ThinkingSystemEnum.TYPE1:
                await execute_llm_react_instruction(cell, swap, send, session)
            elif cell.thinking_system == ThinkingSystemEnum.TYPE2:
                await execute_llm_type2_instruction(cell, swap, send, session)
        elif cell.lang == CellLangEnum.BASH:
            await execute_bash_instruction(cell, swap, send, session)
        else:
            logger.error("unknown cell type", cell_id=cell.id, cell_lang=cell.lang)


if __name__ == "__main__":
    serve()
