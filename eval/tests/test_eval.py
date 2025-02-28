import pytest
from pytest import fail
import subprocess
from eval.types import TroubleshootingQuestion, QNA, VerificationStep
import yaml
import structlog
import tempfile
from pydantic import BaseModel, Field
import opentelemetry.trace as trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from openai_otel import OpenAIAutoInstrumentor
from opsmate.libs.core.trace import traceit
import os
import time
from datetime import timedelta
from typing import Callable
from opsmate.dino.react import run_react
from opsmate.contexts import k8s_ctx
from opsmate.dino import dino
from opsmate.dino.types import Message
import asyncio

logger = structlog.get_logger()


def issues() -> list[TroubleshootingQuestion]:
    with open("./eval/q_n_a.yaml", "r") as f:
        return [QNA(**issue) for issue in yaml.safe_load(f)]


# resource = Resource(
#     attributes={SERVICE_NAME: os.getenv("SERVICE_NAME", "opamate-eval")}
# )

# provider = TracerProvider(resource=resource)
# exporter = OTLPSpanExporter(
#     endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
#     insecure=True,
# )
# processor = BatchSpanProcessor(exporter)
# provider.add_span_processor(processor)
# trace.set_tracer_provider(provider)

# OpenAIAutoInstrumentor().instrument()


@pytest.fixture
def using_eval_cluster():
    current_context = (
        subprocess.run(
            ["kubectl", "config", "current-context"], check=True, capture_output=True
        )
        .stdout.decode("utf-8")
        .strip()
    )
    if current_context != "kind-troubleshooting-eval":
        fail("Not in eval context")

    yield


@pytest.fixture
def with_env(issue: QNA):
    if issue.namespace is not None:
        subprocess.run(["kubectl", "create", "namespace", issue.namespace], check=True)

    yield

    for step in issue.cleanup_steps:
        subprocess.run(step.command.split())

    if issue.namespace is not None:
        subprocess.run(["kubectl", "delete", "namespace", issue.namespace])


@pytest.fixture
def k8s_agent():
    async def run(question: str):
        contexts = await k8s_ctx.resolve_contexts()
        tools = k8s_ctx.resolve_tools()
        return run_react(
            question,
            contexts=contexts,
            tools=tools,
        )

    return run


class OutputScore(BaseModel):
    score: int = Field(
        description="The score between 0 and 100 based on how similar the actual output is to the expected output",
        ge=0,
        le=100,
    )


@dino(model="gpt-4o", response_model=OutputScore)
async def verify_root_cause(
    question: str, candidate_answer: str, expected_output: str
) -> OutputScore:
    return Message.system(
        f"""
You are a sysadmin examiner tasked to verify whether the actual root comes up from the candidate's answer matches the expected root cause.

<Question>
{question}
</Question>

<Expected Output>
{expected_output}
</Expected Output>

<Candidate Answer>
{candidate_answer}
</Candidate Answer>

Please give a score between 0 and 100 based on how similar the candidate's answer is to the expected root cause.
""",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("issue", issues())
@traceit(name="test_load_issues")
async def test_load_issues(
    issue: QNA,
    using_eval_cluster,
    with_env,
    k8s_agent,
):
    for step in issue.steps_to_create_issue:
        # write the manifest to a temp file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(step.manifest.encode("utf-8"))
            f.flush()
            subprocess.run(["kubectl", "apply", "-f", f.name], check=True)

    async for output in await k8s_agent(issue.question):
        logger.info("output", output=output)

    # makes sure the output is similar to the root cause
    if issue.answer_command:
        # execute the command and verify the output
        expected_output = subprocess.run(
            ["/bin/bash", "-c", issue.answer_command],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        score = await verify_root_cause(
            question=issue.question,
            candidate_answer=output,
            expected_output=expected_output.stdout,
        )
        logger.info(
            "output score",
            score=score.score,
            candidate_answer=output,
            expected_output=expected_output.stdout,
        )
        assert score.score > issue.similarity_threshold * 100

    for verification in issue.answer_verification:
        wait_until(lambda: verify_output(verification), timeout=10, period=1)


def verify_output(verification: VerificationStep):

    result = subprocess.run(
        verification.command.split(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = result.stdout
    exit_code = result.returncode
    assert exit_code == verification.exit_code
    assert verification.expected_output in output

    return True


def wait_until(assertion: Callable, timeout: int = 10, period: int = 1):
    mustend = time.time() + timedelta(seconds=timeout).total_seconds()

    while time.time() < mustend:
        try:
            assertion()
            return
        except AssertionError as e:
            logger.error(f"AssertionError: {e}, retrying...")
            time.sleep(period)
            continue
    raise TimeoutError(f"Timeout after {timeout} seconds")
