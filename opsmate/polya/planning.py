import instructor
from anthropic import Anthropic, AsyncAnthropic
from openai import AsyncOpenAI
from opsmate.polya.models import TaskPlan
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

    response.topological_sort()
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
