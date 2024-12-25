from typing import Callable, Any, Dict, Awaitable, Union, List
from enum import Enum
from pydantic import BaseModel, Field
from sugar import dino
import asyncio


class WorkflowType(Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


class WorkflowContext:
    def __init__(self, results: Dict[str, Any] = {}, input: Dict[str, Any] = {}):
        self.results = results
        self.input = input
        self._lock = asyncio.Lock()

    async def set_result(self, key: str, value: Any):
        async with self._lock:
            self.results[key] = value

    def __repr__(self):
        return f"WorkflowContext({self.results})"


class Step:
    step_bags = {}

    def __init__(self, fn: Callable[[WorkflowContext], Awaitable[Any]]):
        self.fn = fn
        self.fn_name = fn.__name__

    def __or__(self, other: Union["Step", "Workflow"]) -> "Workflow":
        return Workflow([self, other], WorkflowType.PARALLEL)

    def __rshift__(self, other: Union["Step", "Workflow"]) -> "Workflow":
        return Workflow([self, other], WorkflowType.SEQUENTIAL)

    def __repr__(self):
        return f"Step({self.fn_name})"

    async def run(self, ctx: WorkflowContext | None = None):
        if ctx is None:
            ctx = WorkflowContext()

        return await self.fn(ctx)


class Workflow:
    def __init__(
        self, steps: List[Union[Step, "Workflow"]], workflow_type: WorkflowType
    ):
        self.steps = steps
        self.workflow_type = workflow_type

    def __or__(self, other: Union[Step, "Workflow"]) -> "Workflow":
        if isinstance(other, Step):
            return Workflow([self, other], WorkflowType.PARALLEL)
        return Workflow([self, other], WorkflowType.PARALLEL)

    def __rshift__(self, other: Union[Step, "Workflow"]) -> "Workflow":
        if isinstance(other, Step):
            return Workflow([self, other], WorkflowType.SEQUENTIAL)
        return Workflow([self, other], WorkflowType.SEQUENTIAL)

    async def run(self, ctx: WorkflowContext = None):
        if self.workflow_type == WorkflowType.PARALLEL:
            tasks = [step.run(ctx) for step in self.steps]
            results = await asyncio.gather(*tasks)

            result_ctx = WorkflowContext()
            for idx, step in enumerate(self.steps):
                await result_ctx.set_result(step.fn_name, results[idx])
            return result_ctx
        else:
            step_ctx = ctx
            for step in self.steps:
                step_ctx = await step.run(step_ctx)
            return step_ctx

    def __repr__(self):
        return f"Workflow({self.steps}, {self.workflow_type})"


def step(fn: Callable):
    _step = Step(fn)
    Step.step_bags[_step.fn_name] = _step.fn

    return _step


class Location(BaseModel):
    city: str = Field(description="The city name")


@step
@dino("gpt-4o-mini", response_model=Location)
async def do_a(ctx):
    return f"Home town of {ctx.input["person_a"]}"


@step
@dino("gpt-4o-mini", response_model=Location)
async def do_b(ctx):
    return f"Home town of {ctx.input["person_b"]}"


@step
@dino("gpt-4o-mini", response_model=str)
async def do_c(ctx):
    """
    You are very good at estimating the distance between two cities.
    """
    a_result = ctx.results["do_a"]
    b_result = ctx.results["do_b"]
    return f"The distance between {a_result.city} and {b_result.city}"


async def main():
    workflow = (do_a | do_b) >> do_c

    print(
        await workflow.run(
            WorkflowContext(
                input={"person_a": "Elon Musk", "person_b": "Boris Johnson"}
            )
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
