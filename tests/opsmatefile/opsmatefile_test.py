import pytest
import tempfile
from opsmate.libs.opsmatefile import load_opsmatefile
from opsmate.libs.core.types import Context, Supervisor, Agent

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
kind: Supervisor
apiVersion: v1
metadata:
  name: supervisor
spec:
  agents:
  - k8s-agent
  - cli-agent
  contexts:
  - the-infra-repo
"""


@pytest.fixture(scope="module")
def opsmatefile():
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as f:
        f.write(fixture)
        f.flush()
        yield f.name


def test_load_opsmatefile(opsmatefile):
    world = load_opsmatefile(opsmatefile)

    assert "the-infra-repo" in world.contexts

    infra_ctx = world.contexts["the-infra-repo"]
    assert isinstance(infra_ctx, Context)

    assert world.supervisor is not None
    assert isinstance(world.supervisor, Supervisor)

    supervisor_agent = world.supervisor_agent()
    assert isinstance(supervisor_agent, Agent)
