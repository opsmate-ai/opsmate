import pytest
import tempfile
from opsmate.libs.opsmatefile import load_opsmatefile
from opsmate.libs.core.types import Context, Supervisor, Agent, DocumentIngestion
from opsmate.tests.base import BaseTestCase

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


class TestOPSMatefile(BaseTestCase):

    @pytest.fixture(scope="module")
    def opsmatefile(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=True) as f:
            f.write(fixture)
            f.flush()
            yield f.name

    def test_load_opsmatefile(self, opsmatefile):
        world = load_opsmatefile(opsmatefile)

        assert "the-infra-repo" in world.contexts

        infra_ctx = world.contexts["the-infra-repo"]
        assert isinstance(infra_ctx, Context)

        assert world.supervisor is not None
        assert isinstance(world.supervisor, Supervisor)

        supervisor_agent = world.supervisor_agent()
        assert isinstance(supervisor_agent, Agent)

        agents = supervisor_agent.spec.agents
        assert len(agents) == 2
        assert "git-agent" in agents
        assert agents["git-agent"].metadata.name == "git-agent"
        assert agents["git-agent"].spec.model == "gpt-4o-mini"
        assert agents["git-agent"].spec.react_mode is False
        assert agents["git-agent"].spec.max_depth == 10
        assert len(agents["git-agent"].spec.task_template.spec.contexts) >= 1
        git_ctxs = [
            ctx.metadata.name
            for ctx in agents["git-agent"].spec.task_template.spec.contexts
        ]
        assert "react" not in git_ctxs
        assert "git" in git_ctxs
        assert "the-infra-repo" in git_ctxs

        assert "k8s-agent" in agents
        assert agents["k8s-agent"].metadata.name == "k8s-agent"
        assert agents["k8s-agent"].spec.model == "gpt-4o"
        assert agents["k8s-agent"].spec.react_mode is True
        assert agents["k8s-agent"].spec.max_depth == 5
        assert len(agents["k8s-agent"].spec.task_template.spec.contexts) == 2
        k8s_ctxs = [
            ctx.metadata.name
            for ctx in agents["k8s-agent"].spec.task_template.spec.contexts
        ]
        assert "react" in k8s_ctxs
        assert "k8s" in k8s_ctxs

        assert supervisor_agent.spec.model == "gpt-o1"
        assert supervisor_agent.spec.react_mode is True
        assert supervisor_agent.spec.max_depth == 11

        contexts = supervisor_agent.spec.task_template.spec.contexts

        context_names = [ctx.metadata.name for ctx in contexts]
        assert len(context_names) == 4
        assert "agent-supervisor" in context_names
        assert "react" in context_names
        assert "sre-manager" in context_names
        assert "the-infra-repo" in context_names

        assert "runbooks" in world.document_ingestions
        assert isinstance(world.document_ingestions["runbooks"], DocumentIngestion)
        assert world.document_ingestions["runbooks"].spec.local_path == "./runbooks"

    def test_ingest_documents(self, opsmatefile):
        world = load_opsmatefile(opsmatefile)

        try:
            world.ingest_documents()
        except Exception as e:
            assert False, f"ingest_documents raised an exception: {e}"
