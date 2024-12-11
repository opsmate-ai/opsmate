import instructor
from opsmate.polya.models import (
    QuestionResponse,
    QuestionResponseSummary,
    InfoGathered,
    Report,
    InitialUnderstandingResponse,
    NonTechnicalQuery,
    ReportExtracted,
)
from anthropic import Anthropic
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import List, Union
import subprocess
from jinja2 import Template
import asyncio


understanding_sys_prompt = """
<assistant>
You are a world class SRE who is good at solving problems. You are tasked to summarise the problem and ask clarifying questions.
</assistant>

<rules>
You will receive a user question that may include a problem description, command line output, logs as the context.
*DO NOT* answer non-technical topics from user, just answer I don't know.
Please maintain a concise and methodical tone in your responses:
- Clearly identify what you are being asked to do.
- Gather all available information
- Identify the constraints and limitations
- Restate the problem in your own words
- Verify you have sufficient information to solve the problem
</rules>

<response_format>
Summary: <Summary of the problem>
Questions: (things you need to know in order to solve the problem)
1. <question 1>
2. <question 2>
...
</response_format>

<important_notes>
- Do not solutionise prematurely.
- Do not ask any tools or permissions related questions.
- Do not ask questions that previously has been answered.
- Only ask 3 questions at most.
- Use markdown in your response.
- Feel free to leave the questions blank if you think you have enough information to solve the problem.
</important_notes>
"""

command_sys_prompt = """
<assistant>
You are a world class SRE who is good at solving problems. You are tasked to provide the command line to be executed to solve the problem.
</assistant>

<rules>
You will receive a high level summary of the problem, and a set of questions that are associated with the problem.
You need to provide the command line to be executed to solve the problem.
</rules>

<response_format>

```
1. description: <description of the command>
   command: <command line to be executed>
2. ...
```
</response_format>

<important_notes>
- If you anticipate the command will generates a lot of output, you should limit the output via piping it to `tail -n 100` command or grepping it with a specific pattern.
- Do not run any command that runs in interactive mode.
- Do not run any command that requires manual intervention.
- Do not run any command that requires user input.
</important_notes>
"""

report_sys_prompt = """
<assistant>
You are a world class SRE who is good at problem solving. You are now given a summary of the problem, and a set of command runs and output observations.
You need to give a detailed report on the problem, and provide some potential solutions on how to resolve the problem.
</assistant>

<response_format>
# Summary
Describe summary of the problem

# Findings
Break down of findings

# Potential solutions
Give some potential solutions on how to resolve the problem, with probability of success.

# Out of scope
Things you have noticed based on the findings however are not related to the problem
</response_format>

<important_notes>
- Use markdown in your response.
- Do not just return the brief summary you are given, but fact in all the findings
- **ONLY** list potential solutions that are relevant to the problem
- The sum of probability of all potential solutions should be added up to 100%
</important_notes>
"""

extra_sys_prompt = """
<assistant-context>
1. As the AI agent you are running inside a pod in the kubernetes cluster.
2. You have access to the following commands:
- kubectl
- helm
3. You have read only access to the cluster
4. Always check the k8s events to understand the context of the problem
5. Avoid using complicated kubectl selector such as `--field-selector involvedObject.name=`
</assistant-context>
"""

modes = {
    # "planner": {
    #     "model": "o1-preview",
    #     "mode": instructor.Mode.JSON_O1,
    # },
    "planner": {
        "model": "gpt-4o",
        "mode": instructor.Mode.TOOLS,
    },
    "executor": {
        "model": "gpt-4o",
        "mode": instructor.Mode.TOOLS,
    },
}


async def initial_understanding(question: str, mode: str = "planner"):
    # anthropic = instructor.from_anthropic(Anthropic())
    openai = instructor.from_openai(AsyncOpenAI(), mode=modes[mode]["mode"])
    question = {
        "role": "user",
        "content": question,
    }

    response: Union[InitialUnderstandingResponse, NonTechnicalQuery] = (
        await openai.messages.create(
            messages=[
                {
                    "role": "user",
                    "content": understanding_sys_prompt + "\n" + extra_sys_prompt,
                },
                question,
            ],
            model=modes[mode]["model"],
            response_model=Union[InitialUnderstandingResponse, NonTechnicalQuery],
        )
    )

    return response


async def __info_gathering(summary: str, question: str, mode: str = "planner"):
    openai = instructor.from_openai(AsyncOpenAI(), mode=modes[mode]["mode"])
    question_prompt = f"""
<summary>
{summary}
</summary>

**Please answer the following question**

<question>
{question}
</question>
"""

    return await openai.messages.create(
        messages=[
            {
                "role": "system",
                "content": command_sys_prompt + "\n" + extra_sys_prompt,
            },
            {
                "role": "user",
                "content": question_prompt,
            },
        ],
        model=modes[mode]["model"],
        response_model=QuestionResponse,
    )


async def __finding(question: QuestionResponse, mode: str = "executor"):
    openai = instructor.from_openai(AsyncOpenAI(), mode=modes[mode]["mode"])

    jinja_template = """
## Issue description

{{ summary }}

## question

{{ question }}

## Here are the commands that are executed to answer the question

{% for command in commands %}
## Command {{ loop.index }}
**Description:** {{ command.description }}

**Command:**
```bash
$ {{ command.command }}
```

Output:
```text
{{ command.execute() }}
```
{% endfor %}
"""
    response: QuestionResponseSummary = await openai.messages.create(
        messages=[
            {
                "role": "user",
                "content": Template(jinja_template).render(
                    summary=question.summary,
                    question=question.question,
                    commands=question.commands,
                ),
            },
            {
                "role": "user",
                "content": "Can you summarise what is going on?",
            },
        ],
        model=modes[mode]["model"],
        response_model=QuestionResponseSummary,
    )

    return response


async def info_gathering(summary: str, question: str):
    question_response = await __info_gathering(summary, question)
    finding = await __finding(question_response)
    return InfoGathered(
        question=question_response.question,
        commands=question_response.commands,
        info_gathered=finding.summary,
    )


async def generate_report(
    summary: str,
    mode: str = "planner",
    info_gathered: List[InfoGathered] = [],
):
    template = """
<context>
## Issue summary

{{ summary }}

## Question raised and answers
{% for info in info_gathered %}
### Question: {{ info.question }}
**Answer:**
{{ info.info_gathered }}
{% endfor %}
</context>

Now please write a detailed report based on the above context.
"""

    content = Template(template).render(summary=summary, info_gathered=info_gathered)

    openai = instructor.from_openai(AsyncOpenAI(), mode=modes[mode]["mode"])
    response: Report = await openai.messages.create(
        messages=[
            {
                "role": "user",
                "content": report_sys_prompt,
            },
            {
                "role": "user",
                "content": content,
            },
        ],
        model=modes[mode]["model"],
        response_model=Report,
    )

    return response


async def report_breakdown(report: Report) -> ReportExtracted:
    """
    Break down the report into a structured format
    """
    openai = instructor.from_openai(AsyncOpenAI(), mode=instructor.Mode.TOOLS)
    report_extracted = await openai.messages.create(
        messages=[
            {
                "role": "user",
                "content": report.content,
            },
        ],
        model="gpt-4o",
        response_model=ReportExtracted,
    )

    # sort the potential solutions by probability
    report_extracted.potential_solutions.sort(key=lambda x: x.probability, reverse=True)
    return report_extracted


async def main():
    iu = await initial_understanding(
        "the deployment payment-service in the payment namespace is failing to rollout"
    )

    print(iu.summary)
    print("Questions:")
    for i, question in enumerate(iu.questions):
        print(f"{i+1}. {question}")

    findings = []
    for i, question in enumerate(iu.questions):
        findings.append(info_gathering(iu.summary, question))

    # Execute all findings in parallel
    info_gathered = await asyncio.gather(*findings)

    report = await generate_report(
        iu.summary,
        mode="executor",
        info_gathered=info_gathered,
    )
    print(report.content)


# Add this to run the async main function
if __name__ == "__main__":
    asyncio.run(main())
