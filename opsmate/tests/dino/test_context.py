import pytest
from os import path

from opsmate.dino import context
from opsmate.dino.context import ContextRegistry
from opsmate.tools import ShellCommand


@pytest.fixture(scope="session", autouse=True)
def context_dir():
    current_dir = path.dirname(path.abspath(__file__))
    context_dir = path.join(current_dir, "fixtures/contexts")
    ContextRegistry.reset()
    ContextRegistry.discover(context_dir)
    yield
    ContextRegistry.reset()


@pytest.mark.asyncio
async def test_builtin_contexts(context_dir):
    contexts = [
        "k8s",
        "cli",
        "terraform",
    ]

    for context in contexts:
        assert context in ContextRegistry.get_contexts()


@pytest.mark.asyncio
async def test_custom_context_load(context_dir):
    gcloud_plugin = ContextRegistry.get_context("gcloud")
    assert gcloud_plugin is not None

    assert (
        await gcloud_plugin.system_prompt()
        == "you are a gcloud SME who is specialised calling gcloud CLI"
    )
    assert gcloud_plugin.description == "gcloud sme"
    assert gcloud_plugin.tools == [ShellCommand]
