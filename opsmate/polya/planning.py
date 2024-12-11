import instructor
from anthropic import Anthropic, AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import List, Union
import subprocess
from jinja2 import Template
import asyncio


planning_sys_prompt = """
<assistant>
You are a world class SRE who is capable of breaking apart tasks into dependant subtasks.
</assistant>

<rules>
- You do not need to break down the task is simple enough to be answered in a single step (e.g. a simple command).
- The subtasks must be independent of each other.
- Your answer must enable the system to complete the user task.
- Do not complete the user task, simply provide a correct compute graph with good specific tasks to ask and relevant subtasks.
- Before completing the list of tasks, think step by step to get a better understanding the problem.
- The tasks must be based on the context provided, DO NOT make up tasks that are unrelated to the context.
- Use as few tasks as possible.
</rules>
"""


class TaskResult(BaseModel):
    """
    TaskResult represents the result of a task
    """

    id: int = Field(description="The unique identifier for the task")
    result: str = Field(description="The result of the task")


class TaskResults(BaseModel):
    """
    TaskResults represent the results of a list of tasks
    """

    results: List[TaskResult] = Field(default_factory=list)


class Task(BaseModel):
    """
    Task represents a single task in a task plan
    """

    id: int = Field(description="The unique identifier for the task")
    task: str = Field(description="Summary of the task")

    subtasks: List[int] = Field(
        default_factory=list,
        description="""
List of the IDs of the subtasks that need to be answered before we can answer the main question.
Use a subtask when anything maybe unknown and we need to ask multiple questions to get the anwer.
        """,
    )

    async def execute(self, with_results: TaskResults) -> TaskResult:
        """
        Execute the task and return the result
        """

        pass


class TaskPlan(BaseModel):
    """
    TaskPlan represents a tree of tasks and subtasks.
    Make sure every task is in the tree, and the graph is a DAG.
    """

    goal: str = Field(description="The goal to achieve")

    subtasks: List[Task] = Field(
        description="List of tasks and subtasks need to be done to complete the user task."
    )

    def topological_sort(self):
        """
        Topological sort the subtasks
        """

        sub_graph = {}
        for task in self.subtasks:
            sub_graph[task.id] = task.subtasks.copy()

        task_map = {task.id: task for task in self.subtasks}

        sorted = []

        while len(sub_graph) > 0:
            nodes = []
            for id, subtasks in sub_graph.items():
                if len(subtasks) == 0:
                    nodes.append(task_map[id])
            for node in nodes:
                del sub_graph[node.id]
                for id, subtasks in sub_graph.items():
                    if node.id in subtasks:
                        subtasks.remove(node.id)
            sorted.extend(nodes)

        return sorted


async def planning(instruction: str, context: str) -> TaskPlan:
    """
    Plan the tasks to complete the user task
    """

    openai = instructor.from_openai(AsyncOpenAI(), mode=instructor.Mode.TOOLS)
    response: TaskPlan = await openai.messages.create(
        messages=[
            {
                "role": "system",
                "content": planning_sys_prompt,
            },
            {
                "role": "user",
                "content": f"""
    <context>
    {context}
    </context>
    """,
            },
            {
                "role": "user",
                "content": instruction,
            },
        ],
        model="gpt-4o",
        response_model=TaskPlan,
    )
    #     anthropic = instructor.from_anthropic(
    #         AsyncAnthropic(), mode=instructor.Mode.ANTHROPIC_TOOLS
    #     )

    #     response: TaskPlan = await anthropic.messages.create(
    #         system=planning_sys_prompt,
    #         messages=[
    #             {
    #                 "role": "user",
    #                 "content": f"""
    # <context>
    # {context}
    # </context>
    # """,
    #             },
    #             {
    #                 "role": "user",
    #                 "content": instruction,
    #             },
    #         ],
    #         model="claude-3-5-sonnet-20241022",
    #         max_tokens=1000,
    #         response_model=TaskPlan,
    #     )
    return response


async def main():
    plan = await planning(
        "How to solve the problem?",
        context="""
## Summary

The 'payment-service' deployment within the 'payment' namespace is failing to roll out successfully in a Kubernetes cluster. This issue is primarily due to problems related to the readiness probe failures and frequent container restart attempts, indicating possible misconfigurations in the service health checks or application dependencies.

## Findings

1. **Readiness Probe Failure:**
   - The readiness probe for the payment-service pods is failing with a 404 status code. This suggests that the health check endpoint configured may be incorrect or the endpoint that the readiness probe is checking is not reachable.

## Recommendation

1. **Verify and Correct Readiness Probe Configuration:**
   - Ensure that the readiness probe's endpoint is correctly configured to check a valid and responsive path within the application.
""",
    )

    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
