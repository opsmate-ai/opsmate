from typing import Callable, Any, Dict, Awaitable, Union, List
from enum import Enum

import asyncio


class WorkflowType(Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


class WorkflowContext:
    def __init__(self, results: Dict[str, Any] = {}):
        self.results = results
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


@step
async def do_a(ctx):
    return "a has been done"


@step
async def do_b(ctx):
    return "b has been done"


@step
async def do_c(ctx):
    print(ctx)
    a_result = ctx.results["do_a"]
    b_result = ctx.results["do_b"]
    return f"{a_result}, {b_result} I am satisfied"


async def main():
    print((do_a | do_b))
    workflow = (do_a | do_b) >> do_c

    print(workflow)

    print(await workflow.run())


if __name__ == "__main__":
    asyncio.run(main())
