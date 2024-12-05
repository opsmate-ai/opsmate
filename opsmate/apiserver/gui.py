from fasthtml.common import *
from opsmate.apiserver.assets import *
from opsmate.libs.providers import Client as ProviderClient
from opsmate.libs.core.types import (
    ExecResults,
    ReactProcess,
    ReactAnswer,
    Observation,
)
from opsmate.libs.agents import supervisor_agent, k8s_agent as _k8s_agent
from opsmate.libs.core.engine.agent_executor import AgentExecutor, AgentCommand
import asyncio
import sqlmodel
from pydantic_settings import BaseSettings
from pydantic import Field
import subprocess
import enum
import pickle
import structlog

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


# Set up the app, including daisyui and tailwind for the chat component
tlink = (Script(src="https://cdn.tailwindcss.com"),)
nav = (
    Nav(
        Div(A("Opsmate Workspace", cls="btn btn-ghost text-xl"), cls="flex-1"),
        Div(
            Label(
                Input(
                    type="checkbox",
                    value="synthwave",
                    cls="theme-controller",
                    hidden=true,
                ),
                sun_icon_svg,
                moon_icon_svg,
                cls="swap swap-rotate",
            ),
        ),
        cls="navbar bg-base-100 shadow-lg mb-4 fixed top-0 left-0 right-0 z-50",
    ),
)

dlink = Link(
    rel="stylesheet",
    href="https://cdn.jsdelivr.net/npm/daisyui@4.11.1/dist/full.min.css",
)


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


def output_cell(cell: Cell):
    if cell.output:
        outputs = pickle.loads(cell.output)
    else:
        outputs = []
    return Div(
        Span(f"Out [{cell.execution_sequence}]:", cls="text-gray-500 text-sm"),
        Div(
            *outputs,
            id=f"cell-output-{cell.id}",
        ),
        cls="px-4 py-2 bg-gray-50 border-t rounded-b-lg overflow-hidden",
    )


def cell_component(cell: Cell, cell_size: int):
    """Renders a single cell component"""
    # Determine if the cell is active
    active_class = "border-green-500 bg-white" if cell.active else "border-gray-300"

    return Div(
        # Add Cell Button Menu
        Div(
            Div(
                Button(
                    plus_icon_svg,
                    tabindex="0",
                    cls="btn btn-ghost btn-xs",
                ),
                Ul(
                    Li(
                        Button(
                            "Insert Above",
                            hx_post=f"/cell/{cell.id}?above=true",
                        )
                    ),
                    Li(
                        Button(
                            "Insert Below",
                            hx_post=f"/cell/{cell.id}?above=false",
                        )
                    ),
                    tabindex="0",
                    cls="dropdown-content z-10 menu p-2 shadow bg-base-100 rounded-box",
                ),
                cls="dropdown dropdown-right",
            ),
            cls="absolute -left-8 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity",
        ),
        # Main Cell Content
        Div(
            # Cell Header
            Div(
                Div(
                    Span(
                        f"In [{cell.execution_sequence}]:", cls="text-gray-500 text-sm"
                    ),
                    # Add cell type selector
                    cls="flex items-center gap-2",
                ),
                Div(
                    Select(
                        Option(
                            "Text Instruction",
                            value=CellEnum.TEXT_INSTRUCTION.value,
                            selected=cell.type == CellEnum.TEXT_INSTRUCTION,
                        ),
                        Option(
                            "Bash",
                            value=CellEnum.BASH.value,
                            selected=cell.type == CellEnum.BASH,
                        ),
                        name="type",
                        hx_put=f"/cell/{cell.id}",
                        hx_trigger="change",
                        cls="select select-sm ml-2",
                    ),
                    Button(
                        trash_icon_svg,
                        hx_delete=f"/cell/{cell.id}",
                        cls="btn btn-ghost btn-sm opacity-0 group-hover:opacity-100 hover:text-red-500",
                        disabled=cell_size == 1,
                    ),
                    Form(
                        Input(type="hidden", value=cell.id, name="cell_id"),
                        Button(
                            run_icon_svg,
                            cls="btn btn-ghost btn-sm",
                        ),
                        ws_connect=f"/cell/run/ws/",
                        ws_send=True,
                        hx_ext="ws",
                    ),
                    cls="ml-auto flex items-center gap-2",
                ),
                id=f"cell-header-{cell.id}",
                cls="flex items-center px-4 py-2 bg-gray-100 border-b justify-between rounded-t-lg overflow-hidden",
            ),
            # Cell Input - Updated with conditional styling
            Div(
                Form(
                    Textarea(
                        cell.input,
                        name="input",
                        cls=f"w-full h-24 p-2 font-mono text-sm border rounded focus:outline-none focus:border-blue-500",
                        placeholder="Enter your instruction here...",
                        id=f"cell-input-{cell.id}",
                    ),
                    Div(
                        hx_put=f"/cell/input/{cell.id}",
                        hx_trigger=f"keyup[!(shiftKey&&keyCode===13)] changed delay:500ms from:#cell-input-{cell.id}",
                        hx_swap=f"#cell-input-form-{cell.id}",
                    ),
                    # xxx: shift+enter is being registered as a newline
                    Div(
                        Input(type="hidden", value=cell.id, name="cell_id"),
                        ws_connect=f"/cell/run/ws/",
                        ws_send=True,
                        hx_ext="ws",
                        hx_trigger=f"keydown[shiftKey&&keyCode===13] from:#cell-input-{cell.id}",
                        hx_swap=f"#cell-input-form-{cell.id}",
                    ),
                    id=f"cell-input-form-{cell.id}",
                ),
                hx_include="input",
                cls="p-4",
            ),
            # Cell Output (if any)
            output_cell(cell),
            cls=f"rounded-lg shadow-sm border {active_class}",  # Apply the active class here
        ),
        cls="group relative",
        key=cell.id,
        id=f"cell-component-{cell.id}",
    )


add_cell_button = (
    Div(
        Button(
            add_cell_svg,
            "Add Cell",
            hx_post="/cell/bottom",
            cls="btn btn-primary btn-sm flex items-center gap-2",
        ),
        id="add-cell-button",
        hx_swap_oob="true",
        cls="flex justify-end",
    ),
)

reset_button = (
    Div(
        Button(
            "Reset",
            cls="btn btn-secondary btn-sm flex items-center gap-1",
        ),
        hx_post="/cells/reset",
        hx_swap_oob="true",
        id="reset-button",
        cls="flex",
    ),
)


def stage_button(stage: dict):
    cls = "px-6 py-3 text-sm font-medium border-0"
    if stage["active"]:
        cls += " bg-white border-b-2 border-b-blue-500 text-blue-600"
    else:
        cls += " bg-gray-50 text-gray-600 hover:bg-gray-100"
    return Button(
        stage["title"],
        hx_put=f"/stage/{stage['id']}/switch",
        cls=cls,
    )


@app.route("/")
async def get():
    active_stage = get_active_stage()
    with sqlmodel.Session(engine) as session:
        # cells = session.exec(sqlmodel.select(Cell).order_by(Cell.sequence)).all()
        cells = await all_cells_ordered(active_stage["id"], session)
        page = Body(
            Div(
                Card(
                    # Header
                    Div(
                        Div(
                            H1(config.session_name, cls="text-2xl font-bold"),
                            Span(
                                "Press Shift+Enter to run cell",
                                cls="text-sm text-gray-500",
                            ),
                            cls="flex flex-col",
                        ),
                        Div(
                            reset_button,
                            add_cell_button,
                            cls="flex gap-2 justify-start",
                        ),
                        cls="mb-4 flex justify-between items-start pt-16",
                    ),
                    render_stage_panel(stages),
                    # Cells Container
                    render_cell_container(cells),
                    # cls="overflow-hidden",
                ),
                cls="max-w-6xl mx-auto p-4 bg-gray-50 min-h-screen",
            )
        )
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
async def put(cell_id: int, input: str = None, type: str = None):
    logger.info("updating cell", cell_id=cell_id, input=input, type=type)

    with sqlmodel.Session(engine) as session:
        selected_cell = await find_cell_by_id(cell_id, session)
        if selected_cell is None:
            return ""

        # update all cells to inactive
        await mark_cell_inactive(selected_cell.stage, session)

        selected_cell.active = True
        if input is not None:
            selected_cell.input = input
        if type is not None:
            if type == CellEnum.TEXT_INSTRUCTION.value:
                selected_cell.type = CellEnum.TEXT_INSTRUCTION
            elif type == CellEnum.BASH.value:
                selected_cell.type = CellEnum.BASH

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
            type=cell.type,
        )
        cell.active = True
        session.add(cell)
        session.commit()

        if cell is None:
            logger.error("cell not found", cell_id=cell_id)
            return

        swap = "beforeend"
        if cell.type == CellEnum.TEXT_INSTRUCTION:
            await execute_llm_instruction(cell, swap, send, session)
        elif cell.type == CellEnum.BASH:
            await execute_bash_instruction(cell, swap, send, session)
        else:
            logger.error("unknown cell type", cell_id=cell.id, type=cell.type)


async def execute_llm_instruction(
    cell: Cell, swap: str, send, session: sqlmodel.Session
):
    logger.info("executing llm instruction", cell_id=cell.id)

    outputs = []
    await send(
        Div(
            *outputs,
            hx_swap_oob="true",
            id=f"cell-output-{cell.id}",
        )
    )
    msg = cell.input.rstrip()
    # execution = executor.supervise(supervisor, msg)
    execution = executor.execute(k8s_agent, msg)

    async for stage in async_wrapper(execution):
        actor = k8s_agent.metadata.name
        output = stage
        partial = None
        if isinstance(output, ExecResults):
            partial = render_exec_results_marakdown(actor, output)
        elif isinstance(output, AgentCommand):
            partial = render_agent_command_marakdown(actor, output)
        elif isinstance(output, ReactProcess):
            partial = render_react_markdown(actor, output)
        elif isinstance(output, ReactAnswer):
            partial = render_react_answer_marakdown(actor, output)
        # elif isinstance(output, Observation):
        #     partial = render_observation_marakdown(actor, output)
        if partial:
            outputs.append(partial)
            await send(
                Div(
                    partial,
                    hx_swap_oob=swap,
                    id=f"cell-output-{cell.id}",
                )
            )

    cell.output = pickle.dumps(outputs)
    session.add(cell)
    session.commit()


async def execute_bash_instruction(
    cell: Cell, swap: str, send, session: sqlmodel.Session
):
    logger.info("executing bash instruction", cell_id=cell.id)
    outputs = []
    await send(
        Div(
            *outputs,
            hx_swap_oob="true",
            id=f"cell-output-{cell.id}",
        )
    )

    script = cell.input.rstrip()
    # execute the script using subprocess with combined output
    process = subprocess.Popen(
        script,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1,
    )

    combined_output = ""
    while True:
        output = process.stdout.readline()
        error = process.stderr.readline()

        if output == "" and error == "" and process.poll() is not None:
            break

        if output:
            combined_output += output
        if error:
            combined_output += error

    output = Div(
        Div(
            f"""**Output**
```
{combined_output}
```
""",
            cls="marked",
        ),
    )
    outputs.append(output)
    cell.output = pickle.dumps(outputs)
    session.add(cell)
    session.commit()
    await send(
        Div(
            *outputs,
            hx_swap_oob=swap,
            id=f"cell-output-{cell.id}",
        )
    )


async def async_wrapper(generator: Generator):
    for stage in generator:
        await asyncio.sleep(0)
        yield stage


def render_cell_container(cells: list[Cell], hx_swap_oob: str = None):
    div = Div(
        *[cell_component(cell, len(cells)) for cell in cells],
        cls="space-y-4 mt-4",
        id="cells-container",
    )
    if hx_swap_oob:
        div.hx_swap_oob = hx_swap_oob
    return div


def render_stage_panel(stages: list[dict]):
    active_stage = get_active_stage()
    return Div(
        Div(
            *[stage_button(stage) for stage in stages],
            cls="flex border-t",
        ),
        # stage Panels
        Div(
            Div(
                Div(
                    Span(
                        f"Current Phase: {active_stage['title']}",
                        cls="font-medium",
                    ),
                    cls="flex items-center gap-2 text-sm text-gray-500",
                ),
                cls="space-y-6",
            ),
            cls="block p-4",
        ),
        # stage description
        Div(
            Div(
                Div(
                    active_stage["description"],
                    cls="text-sm text-gray-700 marked",
                ),
                cls="flex items-center gap-2",
            ),
            cls="bg-blue-50 p-4 rounded-lg border border-blue-100",
        ),
        hx_swap_oob="true",
        id="stage-panel",
    )


def render_react_markdown(agent: str, output: ReactProcess):
    return Div(
        f"""
**{agent} thought process**

| Thought | Action |
| --- | --- |
| {output.thought} | {output.action} |
""",
        cls="marked",
    )


def render_react_answer_marakdown(agent: str, output: ReactAnswer):
    return Div(
        f"""
**{agent} answer**

{output.answer}
""",
        cls="marked",
    )


def render_agent_command_marakdown(agent: str, output: AgentCommand):
    return Div(
        f"""
**{agent} task delegation**

{output.instruction}

<br>
""",
        cls="marked",
    )


def render_observation_marakdown(agent: str, output: Observation):
    return Div(
        f"""
**{agent} observation**

{output.observation}
""",
        cls="marked",
    )


def render_exec_results_marakdown(agent: str, output: ExecResults):
    markdown_outputs = []
    markdown_outputs.append(
        Div(
            f"""
**{agent} results**
""",
            cls="marked",
        )
    )
    for result in output.results:
        output = ""
        column_names = result.table_column_names()
        columns = result.table_columns()

        for idx, column in enumerate(columns):
            output += f"""
**{column_names[idx][0]}**

```
{column}
```
---

"""

        markdown_outputs.append(Div(output, cls="marked"))
    return Div(*markdown_outputs)


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


if __name__ == "__main__":
    serve()
