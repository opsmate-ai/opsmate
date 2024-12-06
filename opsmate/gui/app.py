import structlog
from pydantic import Field
from pydantic_settings import BaseSettings
import sqlmodel
from fasthtml.common import *
from opsmate.gui.models import (
    Cell,
    CellLangEnum,
    stages,
    mark_cell_inactive,
    all_cells_ordered,
    find_cell_by_id,
    get_active_stage,
)
from opsmate.gui.views import (
    tlink,
    dlink,
    picolink,
    nav,
    reset_button,
    add_cell_button,
    render_cell_container,
    render_stage_panel,
    execute_llm_instruction,
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
        for stage in stages:
            cell = session.exec(
                sqlmodel.select(Cell).where(Cell.stage == stage["id"])
            ).first()
            if cell is None:
                cell = Cell(
                    input="",
                    active=True,
                    stage=stage["id"],
                )
                session.add(cell)
        session.commit()


@app.route("/")
async def get():
    with sqlmodel.Session(engine) as session:
        # cells = session.exec(sqlmodel.select(Cell).order_by(Cell.sequence)).all()
        active_stage = get_active_stage()
        cells = await all_cells_ordered(active_stage["id"], session)
        page = home_body(config.session_name, cells, stages)
        return Title(f"{config.session_name}"), page


@app.route("/cell/bottom")
async def post():
    with sqlmodel.Session(engine) as session:
        active_stage = get_active_stage()
        cells = await all_cells_ordered(active_stage["id"], session)
        # update all cells to inactive
        await mark_cell_inactive(active_stage["id"], session)

        # get the highest sequence number
        max_sequence = max(cell.sequence for cell in cells) if cells else 0
        # get the higest execution sequence number
        max_execution_sequence = (
            max(cell.execution_sequence for cell in cells) if cells else 0
        )

        new_cell = Cell(
            input="",
            sequence=max_sequence + 1,
            execution_sequence=max_execution_sequence + 1,
            stage=active_stage["id"],
            active=True,
        )
        session.add(new_cell)
        session.commit()

        cells = await all_cells_ordered(active_stage["id"], session)
        return (
            # Return the new cell to be added
            render_cell_container(cells, hx_swap_oob="true"),
            # Return the button to preserve it
            add_cell_button,
        )


# Add cell manipulation routes
@app.route("/cell/{index}")
async def post(index: int, above: bool = False, session: sqlmodel.Session = None):
    with sqlmodel.Session(engine) as session:
        current_cell = session.exec(
            sqlmodel.select(Cell).where(Cell.id == index)
        ).first()

        cells = await all_cells_ordered(current_cell.stage, session)

        # update all cells to inactive
        await mark_cell_inactive(current_cell.stage, session)

        new_cell = Cell(
            input="",
            active=True,
            stage=current_cell.stage,
        )

        # get the highest execution sequence number
        max_execution_sequence = (
            max(cell.execution_sequence for cell in cells) if cells else 0
        )
        new_cell.execution_sequence = max_execution_sequence + 1

        # get the current sequence number

        if above:
            new_cell.sequence = current_cell.sequence
        else:
            new_cell.sequence = current_cell.sequence + 1

        session.add(new_cell)
        # find all cells with a sequence greater than the current cell
        cells_to_shift = [
            cell for cell in cells if cell.sequence >= current_cell.sequence
        ]
        for cell in cells_to_shift:
            cell.sequence += 1
            session.add(cell)
        session.commit()

        # reload the cells
        cells = await all_cells_ordered(current_cell.stage, session)
        return render_cell_container(cells, hx_swap_oob="true")


@app.route("/cell/{cell_id}")
async def delete(cell_id: int):
    with sqlmodel.Session(engine) as session:
        current_cell = await find_cell_by_id(cell_id, session)

        if current_cell is None:
            return ""

        # find all cells with a sequence greater than the current cell
        cells_to_shift = session.exec(
            sqlmodel.select(Cell)
            .where(Cell.stage == current_cell.stage)
            .where(Cell.sequence > current_cell.sequence)
        ).all()
        for cell in cells_to_shift:
            cell.sequence -= 1
            session.add(cell)

        session.delete(current_cell)
        session.commit()

        cells = await all_cells_ordered(current_cell.stage, session)

        return render_cell_container(cells, hx_swap_oob="true")


@app.route("/cell/{cell_id}")
async def put(cell_id: int, input: str = None, lang: str = None):
    logger.info("updating cell", cell_id=cell_id, input=input, lang=lang)

    with sqlmodel.Session(engine) as session:
        selected_cell = await find_cell_by_id(cell_id, session)
        if selected_cell is None:
            return ""

        # update all cells to inactive
        await mark_cell_inactive(selected_cell.stage, session)

        selected_cell.active = True
        if input is not None:
            selected_cell.input = input
        if lang is not None:
            if lang == CellLangEnum.TEXT_INSTRUCTION.value:
                selected_cell.lang = CellLangEnum.TEXT_INSTRUCTION
            elif lang == CellLangEnum.BASH.value:
                selected_cell.lang = CellLangEnum.BASH

        session.add(selected_cell)
        session.commit()

        cells = await all_cells_ordered(selected_cell.stage, session)

        return render_cell_container(cells, hx_swap_oob="true")


@app.route("/cell/input/{cell_id}")
async def put(cell_id: int, input: str):
    with sqlmodel.Session(engine) as session:
        selected_cell = await find_cell_by_id(cell_id, session)
    if selected_cell is None:
        return ""

    await mark_cell_inactive(selected_cell.stage, session)

    selected_cell.input = input
    selected_cell.active = True
    session.add(selected_cell)
    session.commit()
    return ""


@app.route("/stage/{stage_id}/switch")
async def put(stage_id: str):
    logger.info("switching stage", stage_id=stage_id)
    # mark all stages as inactive
    [stage.update({"active": False}) for stage in stages]
    # mark the selected stage as active
    for stage in stages:
        if stage["id"] == stage_id:
            stage["active"] = True

    with sqlmodel.Session(engine) as session:
        cells = await all_cells_ordered(stage_id, session)

        return (
            render_stage_panel(stages),
            render_cell_container(cells, hx_swap_oob="true"),
        )


@app.route("/cells/reset")
async def post():
    active_stage = get_active_stage()
    with sqlmodel.Session(engine) as session:
        session.exec(sqlmodel.delete(Cell).where(Cell.stage == active_stage["id"]))
        session.commit()
        # create new cells
        cell = Cell(
            input="",
            active=True,
            stage=active_stage["id"],
        )
        session.add(cell)
        session.commit()
        return (
            render_cell_container([cell], hx_swap_oob="true"),
            reset_button,
        )


@app.ws("/cell/run/ws/")
async def ws(cell_id: int, input: str, send, session):
    logger.info("running cell", cell_id=cell_id, input=input)
    # Check authentication token
    if session.get("token", "") != config.token:
        logger.error("unauthorized", token=session.get("token"))
        return  # Exit if unauthorized

    active_stage = get_active_stage()
    with sqlmodel.Session(engine) as session:
        await mark_cell_inactive(active_stage["id"], session)

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
            await execute_llm_instruction(cell, swap, send, session)
        elif cell.lang == CellLangEnum.BASH:
            await execute_bash_instruction(cell, swap, send, session)
        else:
            logger.error("unknown cell type", cell_id=cell.id, cell_lang=cell.lang)


if __name__ == "__main__":
    serve()
