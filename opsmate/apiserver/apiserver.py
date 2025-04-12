from fastapi import FastAPI, Request, Response
from typing import List, Literal
from pydantic import BaseModel, Field
from opsmate.dino.provider import Provider
from opsmate.dino.types import Message, Observation
from opsmate.dino.dino import dino
from opsmate.dino.context import ContextRegistry

from opsmate.libs.core.trace import start_trace
from opentelemetry.instrumentation.starlette import StarletteInstrumentor
import os

app = FastAPI()
api_app = FastAPI()

if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
    from opentelemetry.instrumentation.starlette import StarletteInstrumentor

    start_trace(spans_to_discard=["dbq.dequeue_task"])

    StarletteInstrumentor().instrument_app(app)


from opsmate.gui.app import app as fasthtml_app, startup


class Health(BaseModel):
    status: Literal["ok", "faulty"] = Field(title="status", default="ok")


class Session(BaseModel):
    uuid: str = Field(title="uuid")


@api_app.middleware("http")
async def token_verification(request: Request, call_next):
    if request.url.path == "/v1/healthz":
        return await call_next(request)

    if os.environ.get("OPSMATE_TOKEN"):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response("unauthorized", status_code=401)

        token = auth_header.split(" ")[1]
        if token != os.environ.get("OPSMATE_TOKEN"):
            return Response("unauthorized", status_code=401)
    return await call_next(request)


@api_app.get("/v1/healthz", response_model=Health)
async def health():
    return Health(status="ok")


class Model(BaseModel):
    provider: str = Field(title="provider")
    model: str = Field(title="model")


@api_app.get("/v1/models", response_model=List[Model])
async def models():
    return [
        Model(provider=provider_name, model=m)
        for provider_name, p in Provider.providers.items()
        for m in p.models
    ]


class RunRequest(BaseModel):
    model: str = Field(title="name of the llm model to use")
    instruction: str = Field(title="instruction to execute")
    context: str = Field(title="context to use", default="cli")
    ask: bool = Field(title="ask", default=False)


class RunResponse(BaseModel):
    tool_outputs: str = Field(title="tool outputs")
    observation: str = Field(title="observation")


@api_app.post("/v1/run", response_model=RunResponse)
async def run(request: RunRequest):

    ctx = get_context(request.context)

    @dino("gpt-4o", response_model=Observation, tools=ctx.resolve_tools())
    async def run_command(instruction: str):
        return [
            *await ctx.resolve_contexts(),
            Message.user(instruction),
        ]

    observation: Observation = await run_command(request.instruction)
    return RunResponse(
        tool_outputs="\n".join(
            [output.markdown() for output in observation.tool_outputs]
        ),
        observation=observation.observation,
    )


class ContextNotFound(Exception):
    pass


def get_context(context: str):
    ctx = ContextRegistry.get_context(context)
    if not ctx:
        raise ContextNotFound(f"Context {context} not found")
    return ctx


app.mount("/api", api_app)
app.mount("/", fasthtml_app)

app.add_event_handler("startup", startup)
