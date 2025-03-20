from braintrust import Eval
from autoevals import Factuality
from opsmate.contexts import k8s_ctx
from opsmate.dino import run_react
from opsmate.dino.types import ReactAnswer
from opsmate.libs.core.trace import start_trace
from opentelemetry import trace
import structlog
import os

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer("opsmate.eval")

project_name = "opsmate-eval"
project_id = os.getenv("BRAINTRUST_PROJECT_ID")

if os.getenv("BRAINTRUST_API_KEY") is not None:
    OTEL_EXPORTER_OTLP_ENDPOINT = "https://api.braintrust.dev/otel"
    OTEL_EXPORTER_OTLP_HEADERS = f"Authorization=Bearer {os.getenv('BRAINTRUST_API_KEY')}, x-bt-parent=project_id:{project_id}"

    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = OTEL_EXPORTER_OTLP_ENDPOINT
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = OTEL_EXPORTER_OTLP_HEADERS

    start_trace()


async def k8s_agent(question: str):
    with tracer.start_as_current_span("eval_k8s_agent") as span:
        span.set_attribute("question", question)

        contexts = await k8s_ctx.resolve_contexts()
        tools = k8s_ctx.resolve_tools()
        async for output in run_react(
            question,
            contexts=contexts,
            tools=tools,
            model="claude-3-7-sonnet-20250219",
        ):
            logger.info("output", output=output)

        if isinstance(output, ReactAnswer):
            return output.answer
        else:
            raise ValueError(f"Unexpected output type: {type(output)}")


Eval(
    name=project_name,
    data=lambda: [
        {
            "input": "how many pods are running in the cluster?",
            "expected": "there are 15 pods running in the cluster",
        },
        {
            "input": "how many nodes are running in the cluster?",
            "expected": "there are 4 nodes running in the cluster",
        },
    ],  # Replace with your eval dataset
    task=k8s_agent,  # Replace with your LLM call
    scores=[Factuality],
)

# import asyncio
# asyncio.run(run("how many pods are in the cluster?"))
