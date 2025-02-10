from opsmate.polya.models import TaskPlan, Facts, Fact
import asyncio
from opsmate.tools import KnowledgeRetrieval
from pydantic import BaseModel, Field
from opsmate.dino import dino
from opsmate.dino.types import Message


@dino(
    model="claude-3-5-sonnet-20241022", response_model=Facts, tools=[KnowledgeRetrieval]
)
async def knowledge_retrieval(questions: list[str]) -> str:
    """
    Retrieve relevant information from the knowledge base based on the question
    and break down the information into facts
    Please also list the source of the fact. The source must be a fqdn of the source e.g. https://github.com/opsmate/opsmate/tree
    """
    return "\n".join(questions)


@dino(model="claude-3-5-sonnet-20241022", response_model=list[str])
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


@dino(model="claude-3-5-sonnet-20241022", response_model=TaskPlan)
async def planning(summary: str, facts: list[Fact], instruction: str):
    """
    <assistant>
    You are a world class SRE who is capable of breaking apart tasks into dependant subtasks.
    You are given:
    - a summary of the problem with the findings and solution
    - a list of facts that will help to resolve the problem
    - a user instruction on what to do
    </assistant>

    <rules>
    - Only break down complex tasks that require multiple steps
    - Each subtask must be independent
    - Tasks must be actionable and specific
    - Tasks must relate directly to the given context
    - Think step by step before listing tasks
    - Provide a correct compute graph but don't execute the tasks
    - Use minimum necessary number of tasks
    </rules>

    <important>
    Given the work you are faces are commonly related to Infra as code, a typical route to fix are:
    * git clone the repo and change directory to the repo
    * git checkout to a new branch. the branch name follows the format of opsmate-<short_description>-<6-chars-random-string>
    * make the changes to the code to fix the issue
    * validation is typically performed by the CI so you don't need to run it locally
    * git add, commit and push the changes
    * create a PR to be reviewed by the team
    </important>
    """
    facts = "\n".join(
        [
            f"""
---
fact {idx}:
{fact.fact}
source: {fact.source}
weight: {fact.weight}
---
"""
            for idx, fact in enumerate(facts)
        ]
    )
    return [
        Message.user(f"<summary>{summary}</summary>"),
        Message.user(f"<facts>{facts}</facts>"),
        Message.user(f"<instruction>{instruction}</instruction>"),
    ]


@dino(model="claude-3-5-sonnet-20241022", response_model=Facts)
def load_facts(text: str) -> Facts:
    """
    You are a world class information extractor. You are good at extracting information from a text.
    Please be accurate with the number of facts in the text given.
    """
    return text


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
    facts = await knowledge_retrieval(questions)
    for fact in facts.facts:
        print(fact)
        print("-" * 100)

    task_plan = await planning(
        solution, facts.facts, "how to solve the problem based on the summary and facts"
    )
    print(task_plan)


if __name__ == "__main__":
    asyncio.run(main())
