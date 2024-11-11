import pytest
from pytest import fail
import subprocess
from eval.types import TroubleshootingQuestion, QNA, VerificationStep
import yaml
import structlog
import tempfile
from opsmate.libs.core.engine.agent_executor import AgentExecutor
from opsmate.libs.agents import (
    supervisor_agent,
    k8s_agent,
)
from opsmate.libs.core.types import Agent, ReactAnswer
from openai import OpenAI
import instructor
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

logger = structlog.get_logger()


def issues() -> list[TroubleshootingQuestion]:
    with open("./eval/q_n_a.yaml", "r") as f:
        return [QNA(**issue) for issue in yaml.safe_load(f)]


resource = Resource(
    attributes={SERVICE_NAME: os.getenv("SERVICE_NAME", "opamate-eval")}
)

provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
    insecure=True,
)
processor = BatchSpanProcessor(exporter)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

OpenAIAutoInstrumentor().instrument()


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
    # if issue.namespace is not None:
    #     subprocess.run(["kubectl", "delete", "namespace", issue.namespace], check=True)

    for step in issue.cleanup_steps:
        subprocess.run(step.command.split(), check=True)


@pytest.fixture
def supervisor():
    return supervisor_agent(
        extra_contexts="You are a helpful SRE manager who manages a team of SMEs",
        agents=[
            k8s_agent(
                react_mode=True,
            )
        ],
        model="gpt-4o",
    )


@pytest.fixture
def executor():
    return AgentExecutor(client=OpenAI())


class OutputScore(BaseModel):
    score: int = Field(
        description="The score between 0 and 100 based on how similar the actual output is to the expected output",
        ge=0,
        le=100,
    )


def verify_root_cause(
    question: str, candidate_answer: str, expected_output: str
) -> OutputScore:
    cli = instructor.from_openai(OpenAI())
    return cli.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": f"""
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
            }
        ],
        response_model=OutputScore,
    )


@pytest.mark.parametrize("issue", issues())
@traceit(name="test_load_issues")
def test_load_issues(
    issue: QNA,
    using_eval_cluster,
    with_env,
    supervisor: Agent,
    executor: AgentExecutor,
):
    # for step in issue.steps_to_create_issue:
    #     # write the manifest to a temp file
    #     with tempfile.NamedTemporaryFile(delete=False) as f:
    #         f.write(step.manifest.encode("utf-8"))
    #         f.flush()
    #         subprocess.run(["kubectl", "apply", "-f", f.name], check=True)

    supervisor_output = executor.supervise(
        supervisor,
        # f"In the {issue.namespace} namespace, {issue.question}",
        issue.question,
    )

    for output in supervisor_output:
        agent_name, output = output
        if agent_name == "@supervisor" and isinstance(output, ReactAnswer):
            break

    # makes sure the output is similar to the root cause
    if issue.answer_command:
        # execute the command and verify the output
        expected_output = subprocess.run(
            issue.answer_command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        score = verify_root_cause(
            question=issue.question,
            candidate_answer=output,
            expected_output=expected_output,
        )
        assert score.score > issue.similarity_threshold * 100

    for verification in issue.answer_verification:
        # execute the command and verify the output
        # result = subprocess.run(
        #     verification.command.split(),
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.STDOUT,
        #     text=True,
        # )
        # assert result.returncode == verification.exit_code
        # assert result.stdout == verification.expected_output
        for _ in wait_until():
            verify_output(verification)


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


def wait_until(timeout: int = 10, period: int = 1):
    mustend = time.time() + timeout
    while time.time() < mustend:
        try:
            yield
            return
        except AssertionError as e:
            pass
        time.sleep(period)
    raise TimeoutError(f"Timeout after {timeout} seconds")
