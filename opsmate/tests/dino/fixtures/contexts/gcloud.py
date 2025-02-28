from opsmate.dino import context
from opsmate.tools import ShellCommand


@context(
    name="gcloud",
    tools=[
        ShellCommand,
    ],
)
async def gcloud():
    """gcloud sme"""
    return "you are a gcloud SME who is specialised calling gcloud CLI"
