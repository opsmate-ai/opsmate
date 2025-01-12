from opsmate.plugins import auto_discover
from opsmate.dino import dino
from typing import Literal


@auto_discover(
    author="opsmate",
    version="0.1.0",
)
@dino(model="gpt-4o-mini", response_model=Literal["anthropic", "openai"])
async def my_creator():
    """you are a LLM"""
    return "your creator"
