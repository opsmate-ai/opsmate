from fasthtml.common import *
from opsmate.libs.providers import Client as ProviderClient
from opsmate.libs.core.types import (
    Model,
    ExecResults,
    Task,
    Metadata,
    TaskSpec,
    ReactProcess,
    ReactAnswer,
)
from opsmate.libs.core.engine import exec_task
from opsmate.libs.agents import supervisor_agent, k8s_agent
from opsmate.libs.contexts import k8s_ctx
from opsmate.libs.core.engine.agent_executor import AgentExecutor, AgentCommand
import json
import asyncio

# Set up the app, including daisyui and tailwind for the chat component
tlink = (Script(src="https://cdn.tailwindcss.com"),)
dlink = Link(
    rel="stylesheet",
    href="https://cdn.jsdelivr.net/npm/daisyui@4.11.1/dist/full.min.css",
)
app = FastHTML(hdrs=(tlink, dlink, picolink), exts="ws")

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
    bubble_class = "chat-bubble" if msg["role"] == "user" else "chat-bubble-secondary"
    chat_class = "chat-end" if msg["role"] == "user" else "chat-start"
    return Div(
        Div(msg["role"], cls="chat-header"),
        Div(
            msg["content"],
            id=f"chat-content-{msg_idx}",  # Target if updating the content
            cls=f"chat-bubble {bubble_class}",
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
        H1("Opsmate Workspace"),
        Div(
            *[ChatMessage(msg_idx) for msg_idx, msg in enumerate(messages)],
            id="chatlist",
            cls="chat-box h-[73vh] overflow-y-auto",
        ),
        Form(
            Group(ChatInput(), Button("Send", cls="btn btn-primary")),
            ws_send=True,
            hx_ext="ws",
            ws_connect="/wscon",
            cls="flex space-x-2 mt-2",
        ),
        cls="p-4 max-w-l",
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
        await send(Div(ChatMessage(len(messages) - 1), hx_swap_oob=swap, id="chatlist"))
        actor, output = step
        if actor == "@supervisor":
            if isinstance(output, ReactProcess):
                messages[-1]["content"] = react_table(actor, output)
            elif isinstance(output, ReactAnswer):
                messages[-1]["content"] = react_answer_table(actor, output)
        else:
            if isinstance(output, ExecResults):
                messages[-1]["content"] = exec_results_table(actor, output)
            elif isinstance(output, AgentCommand):
                messages[-1]["content"] = agent_command_table(actor, output)
            elif isinstance(output, ReactProcess):
                messages[-1]["content"] = react_table(actor, output)
        await send(
            Div(
                messages[-1]["content"],
                id=f"chat-content-{len(messages)-1}",
                hx_swap_oob=swap,
            )
        )


async def async_wrapper(generator: Generator):
    for step in generator:
        await asyncio.sleep(0)
        yield step


def react_table(actor: str, output: ReactProcess):
    return Table(
        Tr(Th("Actor"), Td(actor)),
        Tr(Th("Action"), Td(output.action)),
        Tr(Th("Thought"), Td(output.thought)),
        cls="table",
    )


def react_answer_table(actor: str, output: ReactAnswer):
    return Table(
        Tr(Th("Actor"), Td(actor)),
        Tr(Th("Answer"), Td(output.answer)),
        cls="table",
    )


def agent_command_table(actor: str, output: AgentCommand):
    return Table(
        Tr(Th("Actor"), Td(actor)),
        Tr(Th("Command"), Td(output.instruction)),
        cls="table",
    )


def exec_results_table(actor: str, output: ExecResults):
    tables = []
    for result in output.results:
        table = Table(
            Tr(Th("Actor"), *[Td(col[0]) for col in result.table_column_names()]),
            Tr(Td(actor), *[Td(ele) for ele in result.table_columns()]),
            cls="table",
        )
        tables.append(table)
    return Div(*tables)


if __name__ == "__main__":
    serve()
