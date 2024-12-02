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


class Cell(sqlmodel.SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: int = sqlmodel.Field(default=sqlmodel.func.gen_random_uuid(), primary_key=True)
    input: str = sqlmodel.Field(default="")
    output: dict = sqlmodel.Field(
        default_factory=dict, sa_column=sqlmodel.Column(sqlmodel.JSON)
    )

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
        cls="navbar bg-base-100 shadow-lg mb-4 fixed top-0 left-0 right-0",
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

# Add cell state management
cells = [{"id": 1, "input": "", "output": "", "type": "code"}]


def output_cell(cell):
    return Div(
        Span(f"Out [{cell['id']}]:", cls="text-gray-500 text-sm"),
        Div(
            *cell["output"],
            id=f"cell-output-{cell['id']}",
        ),
        cls="px-4 py-2 bg-gray-50 border-t",
    )


def cell_component(cell, index):
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
                    Li(Button("Insert Above", hx_post=f"/cell/add/{index}?above=true")),
                    Li(
                        Button("Insert Below", hx_post=f"/cell/add/{index}?above=false")
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
                Span(f"In [{cell['id']}]:", cls="text-gray-500 text-sm"),
                Div(
                    Button(
                        trash_icon_svg,
                        hx_post=f"/cell/delete/{cell['id']}",
                        cls="btn btn-ghost btn-sm opacity-0 group-hover:opacity-100 hover:text-red-500",
                        disabled=len(cells) == 1,
                    ),
                    Form(
                        Input(type="hidden", value=cell["id"], name="cell_id"),
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
                cls="flex items-center px-4 py-2 bg-gray-100 border-b",
            ),
            # Cell Input
            Div(
                Textarea(
                    cell["input"],
                    cls="w-full h-24 p-2 font-mono text-sm border rounded focus:outline-none focus:border-blue-500",
                    placeholder="Enter your code here...",
                    hx_post=f"/cell/update/{cell['id']}",
                    name="input",
                    # hx_trigger="keyup changed delay:500ms",
                ),
                cls="p-4",
            ),
            # Cell Output (if any)
            output_cell(cell),
            # (
            #     Div(
            #         Span(f"Out [{cell['id']}]:", cls="text-gray-500 text-sm"),
            #         Pre(
            #             cell["output"],
            #             cls="mt-1 text-sm",
            #             id=f"cell-output-{cell['id']}",
            #         ),
            #         cls="px-4 py-2 bg-gray-50 border-t",
            #     )
            #     if cell["output"]
            #     else ""
            # ),
            cls="rounded-lg shadow-sm border",
        ),
        cls="group relative",
        key=cell["id"],
        id=f"cell-component-{cell['id']}",
    )


# Update the main screen route
@app.route("/")
async def get():
    page = Body(
        Div(
            Div(
                # Header
                Div(
                    H1(session_name, cls="text-2xl font-bold"),
                    cls="mb-4 flex justify-between items-center pt-16",
                ),
                # Cells Container
                Div(
                    *[cell_component(cell, i) for i, cell in enumerate(cells)],
                    cls="space-y-4",
                    id="cells-container",
                ),
                cls="max-w-4xl mx-auto p-4 bg-gray-50 min-h-screen",
            )
        )
    )
    return Title(session_name), page


# Add cell manipulation routes
@app.route("/cell/add/{index}")
async def post(index: int, above: bool = False):
    new_id = max(c["id"] for c in cells) + 1
    new_cell = {"id": new_id, "input": "", "output": "", "type": "code"}
    if above:
        cells.insert(index, new_cell)
    else:
        cells.insert(index + 1, new_cell)
    return Div(
        *[cell_component(cell, i) for i, cell in enumerate(cells)],
        id="cells-container",
        hx_swap_oob="true",
    )


@app.route("/cell/delete/{cell_id}")
async def post(cell_id: int):
    if len(cells) > 1:
        cells[:] = [c for c in cells if c["id"] != cell_id]
        return Div(
            *[cell_component(cell, i) for i, cell in enumerate(cells)],
            id="cells-container",
            hx_swap_oob="true",
        )


@app.route("/cell/update/{cell_id}")
async def post(cell_id: int, input: str):
    for cell in cells:
        if cell["id"] == cell_id:
            cell["input"] = input
            break
    return ""


@app.ws("/cell/run/ws/")
async def ws(cell_id: int, send):
    for cell in cells:
        if cell["id"] == cell_id:
            swap = "beforeend"
            cell["output"] = []
            await send(
                Div(
                    *cell["output"],
                    hx_swap_oob="true",
                    id=f"cell-output-{cell['id']}",
                )
            )
            msg = cell["input"].rstrip()
            execution = executor.supervise(supervisor, msg)

            async for step in async_wrapper(execution):
                actor, output = step
                if isinstance(output, ExecResults):
                    partial = render_exec_results_table(output)
                elif isinstance(output, AgentCommand):
                    partial = render_agent_command_table(output)
                elif isinstance(output, ReactProcess):
                    partial = render_react_table(output)
                elif isinstance(output, ReactAnswer):
                    partial = render_react_answer_table(output)
                elif isinstance(output, Observation):
                    partial = render_observation_table(output)
                cell["output"].append(partial)
                await send(
                    Div(
                        partial,
                        hx_swap_oob=swap,
                        id=f"cell-output-{cell['id']}",
                    )
                )
            break


async def async_wrapper(generator: Generator):
    for step in generator:
        await asyncio.sleep(0)
        yield step


def render_react_table(output: ReactProcess):
    return Table(
        Tr(Th("Action"), Td(output.action)),
        Tr(Th("Thought"), Td(output.thought)),
        cls="table",
    )


def render_react_answer_table(output: ReactAnswer):
    return Table(
        Tr(Th("Answer"), Td(output.answer)),
        cls="table",
    )


def render_agent_command_table(output: AgentCommand):
    return Table(
        Tr(Th("Command"), Td(output.instruction)),
        cls="table",
    )


def render_observation_table(output: Observation):
    return Table(
        Tr(Th("Observation"), Td(output.observation)),
        cls="table",
    )


def render_exec_results_table(output: ExecResults):
    tables = []
    for result in output.results:
        table = Table(
            Tr(*[Td(col[0]) for col in result.table_column_names()]),
            Tr(*[Td(ele) for ele in result.table_columns()]),
            cls="table",
        )
        tables.append(table)
    return Div(*tables)


if __name__ == "__main__":
    serve()
