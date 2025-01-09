import instructor
from anthropic import Anthropic, AsyncAnthropic
from openai import AsyncOpenAI
from opsmate.polya.models import TaskPlan, Report
from opsmate.polya.understanding import ReportExtracted, report_breakdown
from typing import List, Union
import subprocess
from jinja2 import Template
import asyncio
from opsmate.tools import ShellCommand, KnowledgeRetrieval
from pydantic import BaseModel, Field
from opsmate.dino import dino
from opsmate.dino.types import Message


class Facts(BaseModel):
    facts: list[str] = Field(description="Facts that will help to resolve the problem")


@dino(model="gpt-4o", response_model=Facts, tools=[KnowledgeRetrieval])
async def knowledge_retrieval(questions: list[str]) -> str:
    """
    Retrieve relevant information from the knowledge base based on the question
    and break down the information into facts
    """
    return "\n".join(questions)


@dino(model="gpt-4o", response_model=list[str])
async def summary_breakdown(summary: str) -> str:
    """
    Break down the summary into a 2 questions that will help to resolve the problem

    <important>
    Question must cover the domain of the problem:

    BAD:
    - how is the service monitor configured?

    GOOD:
    - how is the service monitor of the CRM app in the sales namespace configured?
    </important>
    """
    return [
        Message.user(
            f"""
<context>
{summary}
</context>
"""
        ),
        Message.user("can you break down the summary into a few questions?"),
    ]


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
- Each task must be highly actionable.
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
    solution = """
## Summary
'payment-service' deployment in the 'payment' namespace faces rollout failures due to readiness and liveness probe issues.
Service is not reaching a ready state with zero available replicas marked as ready and 3 replicas unavailable.

## Findings
Service fails readiness and liveness checks with 404 response for '/health' endpoint.

Suggests misconfiguration or application-level issue with serving '/health'.

## Solution
Verify and ensure that the '/health' endpoint is correctly defined and reachable within the application.
This will involve checking configurations and confirming that the HTTP server is set to the correct port and path.
"""
    questions = await summary_breakdown(solution)
    print(questions)
    facts = await knowledge_retrieval(questions)
    for fact in facts.facts:
        print(fact)
        print("-" * 100)


if __name__ == "__main__":
    asyncio.run(main())
