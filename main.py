from opsmate.tools import FilesFind
from opsmate.dino.dino import dino
from opsmate.dino.react import react
from opsmate.dino.tools import dtool
from opsmate.workflow.workflow import step
from typing import Annotated
from pydantic import BaseModel, Field
from opsmate.workflow.workflow import WorkflowContext, StatelessWorkflowExecutor
import asyncio


@dtool
async def count_loc(filepath: Annotated[str, "The path of the exact file"]) -> str:
    """
    Count the lines of code in the given file.
    """

    output = await asyncio.create_subprocess_shell(
        f"wc -l {filepath}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await output.communicate()
    return stdout.decode().strip()


@dtool
async def add(numbers: Annotated[list[int], "The numbers to add"]) -> str:
    """
    Add the given numbers.
    """
    return str(sum(numbers))


# @react(
#     # model="claude-3-5-sonnet-20241022",
#     model="gpt-4o",
#     tools=[FilesFind, count_loc, add],
#     iterable=True,
# )
# async def solver(query: str):
#     """
#     You have access to the file system and the shell.
#     You are given a task, try to solve it by using the tools provided.
#     """
#     return query


class Step(BaseModel):
    description: str = Field(description="The description of the step")


class Plan(BaseModel):
    goal: str = Field(description="The goal of the task")
    steps: list[Step] = Field(
        description="Steps to solve the problem the steps must be in sequential order"
    )


@step
@dino(
    model="gpt-4o",
    response_model=Plan,
)
async def planning(ctx: WorkflowContext):
    """
    You are a world-class planning algorithm.
    You are given a problem, try to break it down into a series of steps in sequential order.
    Think step by step to have a good understanding of the problem
    """
    return ctx.input["problem"]


@react(
    model="gpt-4o",
    tools=[FilesFind, count_loc, add],
    iterable=False,
)
async def _execute_plan(plan: Plan):
    """
    You are given a plan, execute the plan by using the tools provided.
    Please do it step by step.
    """
    return f"""
<plan>
## Goal
{plan.goal}

## Steps
{"---\n".join([step.description for step in plan.steps])}
</plan>
"""


@step
async def execute_plan(ctx: WorkflowContext):
    plan = ctx.step_results
    return await _execute_plan(plan)


async def main():
    workflow = planning >> execute_plan

    executor = StatelessWorkflowExecutor(workflow)

    ctx = WorkflowContext(
        input={
            "problem": "Find all the jypyter notebook files in the current directory and count the number of lines each file, add the result and print it"
        }
    )
    await executor.run(ctx)

    print(ctx.results["execute_plan"])


if __name__ == "__main__":
    asyncio.run(main())
