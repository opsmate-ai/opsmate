from opsmate.dino.types import ToolCall, PresentationMixin
from typing import Dict, Any
from pydantic import Field


class Calculator(ToolCall[int], PresentationMixin):
    """Calculator tool"""

    expr: str = Field(description="The expression to evaluate")

    def __call__(self) -> float:
        return eval(self.expr)

    def markdown(self, context: Dict[str, Any] = {}):
        return f"```\n{self.expr} = {self.output}\n```"
