from pydantic import BaseModel, Field
from opsmate.dino import dino
from opsmate.workflow import Workflow, WorkflowContext, step
from opsmate.workflow.workflow import draw_dot, cond, StatelessWorkflowExecutor
import asyncio


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


@step
@dino("gpt-4o-mini", response_model=str)
async def do_d(ctx):
    return "Hello"


@step
@dino("gpt-4o-mini", response_model=str)
async def do_e(ctx):
    return "Hello"


@step
@dino("gpt-4o-mini", response_model=str)
async def do_f(ctx):
    return "Hello"


async def main():
    root = (do_a | do_b) >> (do_c | (do_d >> do_e)) | do_f
    # root = (do_a | do_b) >> do_c
    # root = do_f >> (do_d | do_e)

    sorted = root.topological_sort()

    for step in sorted:
        print(step, step.prev)

    dot = draw_dot(root, rankdir="TB")
    dot.render(filename="workflow.dot", view=False)

    workflow = StatelessWorkflowExecutor(root)
    ctx = WorkflowContext(input={"person_a": "Elon Musk", "person_b": "Boris Johnson"})
    await workflow.run(ctx)
    print(ctx.results)

    # workflow = Workflow(root)
    # ctx = WorkflowContext(input={"person_a": "Elon Musk", "person_b": "Boris Johnson"})
    # await workflow.run(ctx)
    # print(ctx.results)


if __name__ == "__main__":
    asyncio.run(main())
