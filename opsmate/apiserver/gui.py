from fasthtml.common import *
from opsmate.libs.providers import Client as ProviderClient
from opsmate.libs.core.types import (
    ExecResults,
    ReactProcess,
    ReactAnswer,
    Observation,
)
from opsmate.libs.core.engine import exec_task
from opsmate.libs.agents import supervisor_agent, k8s_agent
from opsmate.libs.contexts import k8s_ctx
from opsmate.libs.core.engine.agent_executor import AgentExecutor, AgentCommand
import json
import asyncio


session_name = os.environ.get("OPSMATE_SESSION_NAME", "session")

add_cell_svg = (
    NotStr(
        """
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <line x1="12" y1="5" x2="12" y2="19"></line>
    <line x1="5" y1="12" x2="19" y2="12"></line>
</svg>
        """
    ),
)

sun_icon_svg = (
    NotStr(
        """
  <!-- sun icon -->
  <svg
    class="swap-off h-10 w-10 fill-current"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24">
    <path
      d="M5.64,17l-.71.71a1,1,0,0,0,0,1.41,1,1,0,0,0,1.41,0l.71-.71A1,1,0,0,0,5.64,17ZM5,12a1,1,0,0,0-1-1H3a1,1,0,0,0,0,2H4A1,1,0,0,0,5,12Zm7-7a1,1,0,0,0,1-1V3a1,1,0,0,0-2,0V4A1,1,0,0,0,12,5ZM5.64,7.05a1,1,0,0,0,.7.29,1,1,0,0,0,.71-.29,1,1,0,0,0,0-1.41l-.71-.71A1,1,0,0,0,4.93,6.34Zm12,.29a1,1,0,0,0,.7-.29l.71-.71a1,1,0,1,0-1.41-1.41L17,5.64a1,1,0,0,0,0,1.41A1,1,0,0,0,17.66,7.34ZM21,11H20a1,1,0,0,0,0,2h1a1,1,0,0,0,0-2Zm-9,8a1,1,0,0,0-1,1v1a1,1,0,0,0,2,0V20A1,1,0,0,0,12,19ZM18.36,17A1,1,0,0,0,17,18.36l.71.71a1,1,0,0,0,1.41,0,1,1,0,0,0,0-1.41ZM12,6.5A5.5,5.5,0,1,0,17.5,12,5.51,5.51,0,0,0,12,6.5Zm0,9A3.5,3.5,0,1,1,15.5,12,3.5,3.5,0,0,1,12,15.5Z" />
  </svg>
    """
    ),
)

moon_icon_svg = (
    NotStr(
        """
  <!-- moon icon -->
  <svg
    class="swap-on h-10 w-10 fill-current"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24">
    <path
      d="M21.64,13a1,1,0,0,0-1.05-.14,8.05,8.05,0,0,1-3.37.73A8.15,8.15,0,0,1,9.08,5.49a8.59,8.59,0,0,1,.25-2A1,1,0,0,0,8,2.36,10.14,10.14,0,1,0,22,14.05,1,1,0,0,0,21.64,13Zm-9.5,6.69A8.14,8.14,0,0,1,7.08,5.22v.27A10.15,10.15,0,0,0,17.22,15.63a9.79,9.79,0,0,0,2.1-.22A8.11,8.11,0,0,1,12.14,19.73Z" />
  </svg>
        """
    ),
)

plus_icon_svg = (
    NotStr(
        """
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <line x1="12" y1="5" x2="12" y2="19"></line>
    <line x1="5" y1="12" x2="19" y2="12"></line>
</svg>
        """
    ),
)

trash_icon_svg = (
    NotStr(
        """
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M3 6h18"></path>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
    <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
</svg>"""
    ),
)

run_icon_svg = (
    NotStr(
        """
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <polygon points="5 3 19 12 5 21 5 3"></polygon>
</svg>
        """
    ),
)
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

app = FastHTML(hdrs=(tlink, dlink, picolink, nav), exts="ws", before=bware)

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

messages = []

# Add cell state management
cells = [{"id": 1, "content": "", "output": "", "type": "code"}]


def CellComponent(cell, index):
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
                    Button(
                        run_icon_svg,
                        hx_post=f"/cell/run/{cell['id']}",
                        cls="btn btn-ghost btn-sm",
                    ),
                    cls="ml-auto flex items-center gap-2",
                ),
                cls="flex items-center px-4 py-2 bg-gray-100 border-b",
            ),
            # Cell Input
            Div(
                Textarea(
                    cell["content"],
                    cls="w-full h-24 p-2 font-mono text-sm border rounded focus:outline-none focus:border-blue-500",
                    placeholder="Enter your code here...",
                    hx_post=f"/cell/update/{cell['id']}",
                    name="content",
                    hx_trigger="keyup changed delay:500ms",
                ),
                cls="p-4",
            ),
            # Cell Output (if any)
            (
                Div(
                    Span(f"Out [{cell['id']}]:", cls="text-gray-500 text-sm"),
                    Pre(cell["output"], cls="mt-1 text-sm"),
                    cls="px-4 py-2 bg-gray-50 border-t",
                )
                if cell["output"]
                else ""
            ),
            cls="rounded-lg shadow-sm border",
        ),
        cls="group relative",
        key=cell["id"],
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
                    *[CellComponent(cell, i) for i, cell in enumerate(cells)],
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
    new_cell = {"id": new_id, "content": "", "output": "", "type": "code"}
    if above:
        cells.insert(index, new_cell)
    else:
        cells.insert(index + 1, new_cell)
    return Div(
        *[CellComponent(cell, i) for i, cell in enumerate(cells)],
        id="cells-container",
        hx_swap_oob="true",
    )


@app.route("/cell/delete/{cell_id}")
async def post(cell_id: int):
    if len(cells) > 1:
        cells[:] = [c for c in cells if c["id"] != cell_id]
        return Div(
            *[CellComponent(cell, i) for i, cell in enumerate(cells)],
            id="cells-container",
            hx_swap_oob="true",
        )


@app.route("/cell/update/{cell_id}")
async def post(cell_id: int, content: str):
    for cell in cells:
        if cell["id"] == cell_id:
            cell["content"] = content
            break
    return ""


@app.route("/cell/run/{cell_id}")
async def post(cell_id: int):
    for cell in cells:
        if cell["id"] == cell_id:
            try:
                # Here you would actually run the code - this is just a mock
                cell["output"] = f"Output for: {cell['content']}"
            except Exception as e:
                cell["output"] = str(e)
            break
    return Div(
        *[CellComponent(cell, i) for i, cell in enumerate(cells)],
        id="cells-container",
        hx_swap_oob="true",
    )


@app.ws("/wscon")
async def ws(msg: str, send):
    messages.append({"role": "user", "content": msg.rstrip()})
    swap = "beforeend"

    # Send the user message to the user (updates the UI right away)
    await send(Div(ChatMessage(len(messages) - 1), hx_swap_oob=swap, id="chatlist"))

    # Send the clear input field command to the user
    await send(ChatInput())

    execution = executor.supervise(supervisor, msg.rstrip())
    async for step in async_wrapper(execution):
        messages.append({"role": "assistant", "content": ""})

        actor, output = step
        print(actor, output.__class__)
        messages[-1]["agent_name"] = actor
        if isinstance(output, ExecResults):
            messages[-1]["content"] = render_exec_results_table(output)
        elif isinstance(output, AgentCommand):
            messages[-1]["content"] = render_agent_command_table(output)
        elif isinstance(output, ReactProcess):
            messages[-1]["content"] = render_react_table(output)
        elif isinstance(output, ReactAnswer):
            messages[-1]["content"] = render_react_answer_table(output)
        elif isinstance(output, Observation):
            messages[-1]["content"] = render_observation_table(output)
        await send(Div(ChatMessage(len(messages) - 1), hx_swap_oob=swap, id="chatlist"))


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
