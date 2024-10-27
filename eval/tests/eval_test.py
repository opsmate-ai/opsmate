import pytest
from pytest import fail
import subprocess
from eval.types import TroubleshootingQuestion
import yaml
import structlog
import tempfile
from opsmate.libs.core.engine.agent_executor import gen_agent_commands, AgentExecutor
from opsmate.libs.agents import (
    supervisor_agent,
    k8s_agent,
)
from opsmate.libs.core.types import Agent, ReactAnswer
from openai import OpenAI
import instructor
from pydantic import BaseModel, Field

logger = structlog.get_logger()


def issues() -> list[TroubleshootingQuestion]:
    with open("./eval/issues.yaml", "r") as f:
        return [TroubleshootingQuestion(**issue) for issue in yaml.safe_load(f)]


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
def with_namespace(issue: TroubleshootingQuestion):
    subprocess.run(["kubectl", "create", "namespace", issue.namespace], check=True)
    yield
    subprocess.run(["kubectl", "delete", "namespace", issue.namespace], check=True)


@pytest.fixture
def supervisor():
    return supervisor_agent(
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


class RootCauseScore(BaseModel):
    score: int = Field(
        description="The score between 0 and 100 based on how similar the actual output is to the expected output",
        ge=0,
        le=100,
    )


def verify_root_cause(
    question: str, candidate_answer: str, expected_root_cause: str
) -> RootCauseScore:
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

<Expected Root Cause>
{expected_root_cause}
</Expected Root Cause>

<Candidate Answer>
{candidate_answer}
</Candidate Answer>

Please give a score between 0 and 100 based on how similar the candidate's answer is to the expected root cause.
""",
            }
        ],
        response_model=RootCauseScore,
    )


@pytest.mark.parametrize("issue", issues())
def test_load_issues(
    issue: TroubleshootingQuestion,
    using_eval_cluster,
    with_namespace,
    supervisor: Agent,
    executor: AgentExecutor,
):
    for step in issue.steps_to_create_issue:
        # write the manifest to a temp file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(step.manifest.encode("utf-8"))
            f.flush()
            subprocess.run(["kubectl", "apply", "-f", f.name], check=True)

    supervisor_output = executor.supervise(
        supervisor,
        f"In the {issue.namespace} namespace, {issue.question}",
    )

    for output in supervisor_output:
        agent_name, output = output
        if agent_name == "@supervisor" and isinstance(output, ReactAnswer):
            break

    # makes sure the output is similar to the root cause
    score = verify_root_cause(
        question=issue.question,
        candidate_answer=output,
        expected_root_cause=issue.root_cause,
    )
    assert score.score > 60
