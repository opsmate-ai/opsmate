import pytest
from opsmate.dino.react import react
from opsmate.dino.context import context
from opsmate.dino import dtool, dino
from opsmate.dino.types import ToolCall
from typing import Literal
from pydantic import Field
import structlog

logger = structlog.get_logger(__name__)

# import tempfile
# from opsmate.libs.opsmatefile import load_opsmatefile
# from opsmate.libs.core.types import Context, Supervisor, Agent, DocumentIngestion
# from opsmate.tests.base import BaseTestCase

fixture = """
kind: Context
apiVersion: v1
metadata:
  name: the-infra-repo
  description: Context for the infra repo
spec:
  contexts:
  - os
  data: |
    this is the infra repo context
---
kind: Context
apiVersion: v1
metadata:
  name: sre-manager
  description: Context for the SRE manager
spec:
  contexts:
  - the-infra-repo
  data: |
    you are a helpful SRE manager who manages a team of SMEs
---
kind: Supervisor
apiVersion: v1
metadata:
  name: supervisor
spec:
  model: gpt-o1
  max_depth: 11
  agents:
  - name: k8s-agent
    model: gpt-4o
    react_mode: true
    max_depth: 5
  - name: git-agent
    model: gpt-4o-mini
    react_mode: false
    max_depth: 10
    extra_contexts:
    - the-infra-repo
  contexts:
  - sre-manager
  - the-infra-repo
---
kind: DocumentIngestion
apiVersion: v1
metadata:
  name: runbooks
spec:
  local_path: ./runbooks
"""


@context("goat-iac")
def infra_repo(repo_name: str):
    return f"""
You manages the {repo_name} repo manages the infra via Infra as Code.
"""


@context("sre-manager")
def sre_manager():
    return """
<sre-manager>
You are a helpful SRE manager who manages a team of SMEs.
Delegate task to the adequate agent to handle the task.
</sre-manager>
"""


@dtool
def tf_apply() -> str:
    return "terraform has been applied"


@dtool
def kubectl() -> str:
    return "kubectl command has succeeded"


@dtool
@react(
    model="gpt-4o",
    contexts=[infra_repo("goat-iac")],
    max_iter=3,
    iterable=False,
    callback=lambda x: logger.info("processing", result=x, agent="k8s_agent"),
    tools=[kubectl],
)
async def k8s_agent(
    k8s_query: str,
) -> str:  # xxx: look into pydantic serialization warning
    """
    k8s agent manages the kubernetes aspect of the infra repo.
    """
    return k8s_query


@dtool
@react(
    model="gpt-4o",
    contexts=[infra_repo("goat-iac")],
    max_iter=10,
    iterable=False,
    callback=lambda x: logger.info("processing", result=x, agent="terraform_agent"),
    tools=[tf_apply],
)
async def terraform_agent(
    terraform_query: str,
) -> str:  # xxx: look into pydantic serialization warning
    """
    terraform agent manages the iac aspect of the infra repo.
    """
    return terraform_query


@react(
    model="gpt-4o",
    tools=[k8s_agent, terraform_agent],
    contexts=[infra_repo("goat-iac"), sre_manager()],
    max_iter=11,
    iterable=False,
    callback=lambda x: logger.info("processing", result=x, agent="sre_manager"),
)
async def sre_manager(query: str):
    return query


# infra_repo_ctx = """
# You manages the infra repo manages the infra via Infra as Code.
# """

# sre_manager_ctx = """
# You are a helpful SRE manager who manages a team of SMEs.
# """


@dino("gpt-4o-mini", response_model=Literal["Good", "Bad"])
async def good_or_bad(answer: str):
    return "return whether result is success or failed: " + answer


@pytest.mark.asyncio
async def test_sre_manager():
    answer = await sre_manager("terraform apply the repo")
    assert await good_or_bad(answer.answer) == "Good"

    answer = await sre_manager("get all the pods in the default namespace")
    assert await good_or_bad(answer.answer) == "Good"
