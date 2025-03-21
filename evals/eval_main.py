from braintrust import Eval, EvalHooks
from autoevals.ragas import AnswerCorrectness
from braintrust_core.score import Scorer, Score
from opsmate.contexts import k8s_ctx
from opsmate.dino import run_react
from opsmate.dino.types import ReactAnswer
from opsmate.libs.core.trace import start_trace
from opentelemetry import trace
import structlog
import os
import subprocess
import jinja2

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


class OpsmateScorer(Scorer):
    def _run_eval_sync(self, output, expected=None, **kwargs) -> Score:
        metadata = kwargs.get("metadata", {})
        cmds = {}
        for key, cmd in metadata.get("cmds", {}).items():
            cmds[key] = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

        expected = jinja2.Template(expected).render(**cmds)

        logger.info("rendered expected", expected=expected)
        answer_correctness = AnswerCorrectness()
        score = answer_correctness.eval(
            input=kwargs.get("input"),
            output=output,
            expected=expected,
        )
        score.metadata["cmds"] = cmds
        score.metadata["rendered_expected"] = expected

        return score


async def k8s_agent(question: str, hooks: EvalHooks):
    with tracer.start_as_current_span("eval_k8s_agent") as span:
        span.set_attribute("question", question)

        contexts = await k8s_ctx.resolve_contexts()
        tools = k8s_ctx.resolve_tools()
        async for output in run_react(
            question,
            contexts=contexts,
            tools=tools,
            model=hooks.metadata.get("model"),
        ):
            logger.info("output", output=output)

        if isinstance(output, ReactAnswer):
            return output.answer
        else:
            raise ValueError(f"Unexpected output type: {type(output)}")


test_cases = [
    {
        "input": "how many pods are running in the cluster?",
        "expected": "there are {{pod_num}} pods running in the cluster",
        "tags": ["k8s", "simple"],
        "metadata": {
            "cmds": {
                "pod_num": "kubectl get pods -A --no-headers | wc -l",
            }
        },
    },
    {
        "input": "how many nodes are running in the cluster?",
        "expected": "there are {{node_num}} nodes running in the cluster",
        "tags": ["k8s", "simple"],
        "metadata": {
            "cmds": {
                "node_num": "kubectl get nodes --no-headers | wc -l",
            }
        },
    },
]

# models = ["claude-3-7-sonnet-20250219", "gpt-4o"]
models = ["gpt-4o"]
test_cases = [
    {
        **case,
        "tags": [model, *case["tags"]],
        "metadata": {"model": model, **case["metadata"]},
    }
    for model in models
    for case in test_cases
]

Eval(
    name=project_name,
    data=test_cases,
    task=k8s_agent,
    scores=[OpsmateScorer],
)

# import asyncio
# asyncio.run(run("how many pods are in the cluster?"))
