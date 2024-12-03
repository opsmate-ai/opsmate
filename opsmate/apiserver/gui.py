from fasthtml.common import *
from opsmate.apiserver.assets import *
from opsmate.libs.providers import Client as ProviderClient
from opsmate.libs.core.types import (
    ExecResults,
    ReactProcess,
    ReactAnswer,
    Observation,
)
from opsmate.libs.agents import supervisor_agent, k8s_agent
from opsmate.libs.core.engine.agent_executor import AgentExecutor, AgentCommand
import asyncio
import sqlmodel
import subprocess
import enum
import pickle

# start a sqlite database
engine = sqlmodel.create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}
)


def on_startup():
    sqlmodel.SQLModel.metadata.create_all(engine)


class CellType(enum.Enum):
    TEXT = "text"
    BASH = "bash"


class Cell(sqlmodel.SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: int = sqlmodel.Field(primary_key=True)
    input: str = sqlmodel.Field(default="")
    # output: dict = sqlmodel.Field(sa_column=sqlmodel.Column(sqlmodel.JSON))
    output: bytes = sqlmodel.Field(sa_column=sqlmodel.Column(sqlmodel.LargeBinary))
    type: CellType = sqlmodel.Field(
        sa_column=sqlmodel.Column(
            sqlmodel.Enum(CellType), default=CellType.TEXT, nullable=True, index=False
        )
    )
    sequence: int = sqlmodel.Field(default=0)
    execution_sequence: int = sqlmodel.Field(default=0)

    class Config:
        arbitrary_types_allowed = True


session_name = os.environ.get("OPSMATE_SESSION_NAME", "session")

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
    if os.environ.get("OPSMATE_TOKEN"):
        if req.query_params.get("token") != os.environ.get("OPSMATE_TOKEN"):
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
        cell = session.exec(sqlmodel.select(Cell)).first()
        if cell is None:
            cell = Cell(input="", type=CellType.TEXT)
            session.add(cell)
            session.commit()


client_bag = ProviderClient.clients_from_env()

executor = AgentExecutor(client_bag, ask=False)

supervisor = supervisor_agent(
    model="gpt-4o",
    provider="openai",
    extra_contexts="You are a helpful SRE manager who manages a team of SMEs",
    agents=[
        k8s_agent(
            model="gpt-4o",
            provider="openai",
            react_mode=True,
            max_depth=10,
        ),
    ],
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
        cls="px-4 py-2 bg-gray-50 border-t",
    )


def cell_component(cell: Cell, cell_size: int):
    """Renders a single cell component"""
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
                            hx_post=f"/cell/add/{cell.id}?above=true",
                        )
                    ),
                    Li(
                        Button(
                            "Insert Below",
                            hx_post=f"/cell/add/{cell.id}?above=false",
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
                            "Text", value="text", selected=cell.type == CellType.TEXT
                        ),
                        Option(
                            "Bash", value="bash", selected=cell.type == CellType.BASH
                        ),
                        name="type",
                        hx_post=f"/cell/update/{cell.id}",
                        hx_trigger="change",
                        cls="select select-sm ml-2",
                    ),
                    Button(
                        trash_icon_svg,
                        hx_post=f"/cell/delete/{cell.id}",
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
                cls="flex items-center px-4 py-2 bg-gray-100 border-b justify-between",
            ),
            # Cell Input - Updated with conditional styling
            Div(
                Textarea(
                    cell.input,
                    cls=f"w-full h-24 p-2 font-mono text-sm border rounded focus:outline-none focus:border-blue-500",
                    placeholder="Enter your instruction here...",
                    hx_post=f"/cell/update/input/{cell.id}",
                    name="input",
                    hx_trigger="keyup changed delay:500ms",
                ),
                cls="p-4",
            ),
            # Cell Output (if any)
            output_cell(cell),
            cls="rounded-lg shadow-sm border",
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
            hx_post="/cell/add/bottom",
            cls="btn btn-primary btn-sm flex items-center gap-2",
        ),
        id="add-cell-button",
        hx_swap_oob="true",
        cls="flex justify-end",
    ),
)


def with_session(func):
    async def wrapper(*args, **kwargs):
        with sqlmodel.Session(engine) as session:
            try:
                # Remove session from kwargs if it exists to avoid duplicate argument
                kwargs.pop("session", None)
                return await func(*args, session=session, **kwargs)
            except Exception as e:
                session.rollback()
                raise e

    return wrapper


# Update the main screen route
@app.route("/")
async def get():
    with sqlmodel.Session(engine) as session:
        cells = session.exec(sqlmodel.select(Cell).order_by(Cell.sequence)).all()
        page = Body(
            Div(
                Div(
                    # Header
                    Div(
                        H1(session_name, cls="text-2xl font-bold"),
                        add_cell_button,
                        cls="mb-4 flex justify-between items-center pt-16",
                    ),
                    # Cells Container
                    Div(
                        *[cell_component(cell, len(cells)) for cell in cells],
                        cls="space-y-4",
                        id="cells-container",
                    ),
                    cls="max-w-4xl mx-auto p-4 bg-gray-50 min-h-screen",
                )
            )
        )
        return Title(session_name), page


@app.route("/cell/add/bottom")
async def post():
    with sqlmodel.Session(engine) as session:
        cells = session.exec(sqlmodel.select(Cell).order_by(Cell.sequence)).all()
        # get the highest sequence number
        max_sequence = max(cell.sequence for cell in cells) if cells else 0
        # get the higest execution sequence number
        max_execution_sequence = (
            max(cell.execution_sequence for cell in cells) if cells else 0
        )
        new_cell = Cell(
            input="",
            type=CellType.TEXT,
            sequence=max_sequence + 1,
            execution_sequence=max_execution_sequence + 1,
        )
        session.add(new_cell)
        session.commit()

        session.refresh(new_cell)
        return (
            # Return the new cell to be added
            Div(
                cell_component(new_cell, len(cells) + 1),
                id="cells-container",
                hx_swap_oob="beforeend",
            ),
            # Return the button to preserve it
            add_cell_button,
        )


# Add cell manipulation routes
@app.route("/cell/add/{index}")
async def post(index: int, above: bool = False, session: sqlmodel.Session = None):
    with sqlmodel.Session(engine) as session:
        current_cell = session.exec(
            sqlmodel.select(Cell).where(Cell.id == index)
        ).first()
        cells = session.exec(sqlmodel.select(Cell).order_by(Cell.sequence)).all()

        new_cell = Cell(input="", type=CellType.TEXT)
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
        cells = session.exec(sqlmodel.select(Cell).order_by(Cell.sequence)).all()
        return Div(
            *[cell_component(cell, len(cells)) for cell in cells],
            id="cells-container",
            hx_swap_oob="true",
        )


@app.route("/cell/delete/{cell_id}")
async def post(cell_id: int):
    with sqlmodel.Session(engine) as session:
        current_cell = session.exec(
            sqlmodel.select(Cell).where(Cell.id == cell_id)
        ).first()

        if current_cell is None:
            return ""

        # find all cells with a sequence greater than the current cell
        cells_to_shift = session.exec(
            sqlmodel.select(Cell).where(Cell.sequence > current_cell.sequence)
        ).all()
        for cell in cells_to_shift:
            cell.sequence -= 1
            session.add(cell)

        session.delete(current_cell)
        session.commit()

        cells = session.exec(sqlmodel.select(Cell).order_by(Cell.sequence)).all()

        return Div(
            *[cell_component(cell, len(cells)) for cell in cells],
            id="cells-container",
            hx_swap_oob="true",
        )


@app.route("/cell/update/{cell_id}")
async def post(cell_id: int, input: str = None, type: str = None):
    with sqlmodel.Session(engine) as session:
        selected_cell = session.exec(
            sqlmodel.select(Cell).where(Cell.id == cell_id)
        ).first()
        if selected_cell is None:
            return ""
        if input is not None:
            selected_cell.input = input
        if type is not None:
            if type == "text":
                selected_cell.type = CellType.TEXT
            elif type == "bash":
                selected_cell.type = CellType.BASH

        session.add(selected_cell)
        session.commit()

        # xxx: use proper count statement later...
        cells_len = len(session.exec(sqlmodel.select(Cell)).all())
        return Div(
            cell_component(selected_cell, cells_len),
            id=f"cell-component-{selected_cell.id}",
            hx_swap_oob="true",
        )


@app.route("/cell/update/input/{cell_id}")
async def post(cell_id: int, input: str):
    with sqlmodel.Session(engine) as session:
        selected_cell = session.exec(
            sqlmodel.select(Cell).where(Cell.id == cell_id)
        ).first()
    if selected_cell is None:
        return ""
    selected_cell.input = input
    session.add(selected_cell)
    session.commit()
    return ""


@app.ws("/cell/run/ws/")
async def ws(cell_id: int, send):
    with sqlmodel.Session(engine) as session:
        cell = session.exec(sqlmodel.select(Cell).where(Cell.id == cell_id)).first()
        if cell is None:
            return

        swap = "beforeend"
        if cell.type == CellType.TEXT:
            await execute_llm_instruction(cell, swap, send, session)
        elif cell.type == CellType.BASH:
            await execute_bash_instruction(cell, swap, send, session)


async def execute_llm_instruction(
    cell: Cell, swap: str, send, session: sqlmodel.Session
):
    outputs = []
    await send(
        Div(
            *outputs,
            hx_swap_oob="true",
            id=f"cell-output-{cell.id}",
        )
    )
    msg = cell.input.rstrip()
    execution = executor.supervise(supervisor, msg)

    async for step in async_wrapper(execution):
        actor, output = step
        partial = None
        if isinstance(output, ExecResults):
            partial = render_exec_results_marakdown(actor, output)
        elif isinstance(output, AgentCommand):
            partial = render_agent_command_marakdown(actor, output)
        elif isinstance(output, ReactProcess):
            partial = render_react_markdown(actor, output)
        elif isinstance(output, ReactAnswer):
            if actor == "@supervisor":
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
    for step in generator:
        await asyncio.sleep(0)
        yield step


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


if __name__ == "__main__":
    serve()
