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


# Chat message component (renders a chat bubble)
# Now with a unique ID for the content and the message
def ChatMessage(msg_idx, **kwargs):
    msg = messages[msg_idx]
    chat_class = "chat-end" if msg["role"] == "user" else "chat-start"

    assistant_name = msg["role"]
    if "agent_name" in msg:
        assistant_name = msg["agent_name"]
    return Div(
        Div(assistant_name, cls="chat-header"),
        Div(
            msg["content"],
            id=f"chat-content-{msg_idx}",  # Target if updating the content
            cls=f"chat-bubble",
        ),
        id=f"chat-message-{msg_idx}",  # Target if replacing the whole message
        cls=f"chat {chat_class}",
        **kwargs,
    )


# The input field for the user message. Also used to clear the
# input field after sending a message via an OOB swap
def ChatInput():
    return Input(
        type="text",
        name="msg",
        id="msg-input",
        placeholder="Type a message",
        cls="input input-bordered w-full",
        hx_swap_oob="true",
    )


# The main screen
@app.route("/")
def get():
    page = Body(
        Div(
            Div(
                Div(
                    *[ChatMessage(msg_idx) for msg_idx, msg in enumerate(messages)],
                    id="chatlist",
                    cls="chat-box h-[80vh] overflow-y-auto mb-0",
                ),
                Form(
                    Group(ChatInput(), Button("Send", cls="btn btn-primary")),
                    ws_send=True,
                    hx_ext="ws",
                    ws_connect="/wscon",
                    cls="flex space-x-2 fixed bottom-2 left-4 right-4 max-w-4xl mx-auto",
                ),
                cls="max-w-4xl mx-auto relative h-screen pb-20 pt-16",
            ),
            cls="w-full bg-base-200",
        ),
        # Add auto-scroll script
        Script(
            """
            document.addEventListener("htmx:wsAfterMessage", e => {
                const messagesDiv = document.getElementById("chatlist");
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            })
        """
        ),
    )
    return Title("Chatbot Demo"), page


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
