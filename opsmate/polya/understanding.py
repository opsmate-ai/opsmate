import instructor
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
You need to summarise the problem statement in a concise manner.
</assistant>

<response_format>
# Summary
Describe summary of the problem

# Findings
Break down of findings

# Recommendation
Recommendation on how to resolve the problem based on the findings.

# Out of scope
Things you have noticed based on the findings however are not related to the problem
</response_format>

<important_notes>
- Use markdown in your response.
- Do not just return the brief summary you are given, but fact in all the findings
- Please list the recommendation and grade them from 0 to 100, list the top 3 recommendations from highest to lowest with score 80 or above.
- If a subject does not contribute to the problem, DO NOT include it in the recommendation.
</important_notes>
"""

extra_sys_prompt = """
<assistant-context>
1. As the AI agent you are running inside a pod in the kubernetes cluster.
2. You have access to the following commands:
- kubectl
- helm
3. You have read only access to the cluster
</assistant-context>
"""


class NonTechnicalQuery(BaseModel):
    """
    The non-technical query from user
    """

    reason: str = Field(
        description="The reason why this query is not technical related"
    )


class UnderstandingResponse(BaseModel):
    """
    This is the response format for the summary section.
    """

    summary: str
    questions: List[str]

    def prompt(self):
        return f"""
<command-question>
## Summary of the problem

{self.summary}

## Questions

{f"\n".join([f"{i+1}. {question}" for i, question in enumerate(self.questions)])}
</command-question>
"""


class Command(BaseModel):
    """
    The command line to be executed
    """

    command: str = Field(description="The command line to be executed")
    description: str = Field(
        description="what are the informations are provided by the command execution"
    )

    def execute(self):
        """
        Execute the command and return the output
        """
        try:
            result = subprocess.run(
                self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            return result.stdout
        except subprocess.SubprocessError as e:
            return str(e)


class OutputSummary(BaseModel):
    """
    The summary of the output
    """

    summary: str


class Output(BaseModel):
    command: Command
    output_summary: OutputSummary


class Report(BaseModel):
    """
    The detailed report based on the high level summary and the findings
    """

    content: str


modes = {
    "planner": {
        "model": "o1-preview",
        "mode": instructor.Mode.JSON_O1,
    },
    # "planner": {
    #     "model": "gpt-4o",
    #     "mode": instructor.Mode.TOOLS,
    # },
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

    response: Union[UnderstandingResponse, NonTechnicalQuery] = (
        await openai.messages.create(
            messages=[
                {
                    "role": "user",
                    "content": understanding_sys_prompt + "\n" + extra_sys_prompt,
                },
                question,
            ],
            model=modes[mode]["model"],
            response_model=Union[UnderstandingResponse, NonTechnicalQuery],
        )
    )

    return response


async def info_gathering(question: UnderstandingResponse, mode: str = "planner"):
    openai = instructor.from_openai(AsyncOpenAI(), mode=modes[mode]["mode"])
    response: List[Command] = await openai.messages.create(
        messages=[
            {
                "role": "user",
                "content": command_sys_prompt + "\n" + question.prompt(),
            },
        ],
        model=modes[mode]["model"],
        response_model=List[Command],
    )

    return response


async def finding(summary: str, command: Command, mode: str = "executor"):
    openai = instructor.from_openai(AsyncOpenAI(), mode=modes[mode]["mode"])
    response: OutputSummary = await openai.messages.create(
        messages=[
            {
                "role": "user",
                "content": f"""
## Issue summary

{summary}

## Command

Description: {command.description}

Actual command:
```
{command.command}
```

Output:
```
{command.execute()}
```
                """,
            },
            {
                "role": "user",
                "content": "Can you summarise what is going on?",
            },
        ],
        model=modes[mode]["model"],
        response_model=OutputSummary,
    )

    return response


async def generate_report(
    summary: str,
    mode: str = "planner",
    outputs: List[Output] = [],
):
    template = """
<context>
## Issue summary

{{ summary }}

## Output summaries
{% for output in outputs %}
### Description: {{ output.command.description }}

Command:
```bash
{{ output.command.command }}
```

Output:
```text
{{ output.output_summary.summary }}
```
{% endfor %}
</context>

Now please write a detailed report based on the above context.
"""

    content = Template(template).render(summary=summary, outputs=outputs)

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


async def main():
    iu = await initial_understanding(
        "the deployment payment-service in the payment namespace is failing to rollout"
    )

    print(iu.summary)
    print("Questions:")
    for i, question in enumerate(iu.questions):
        print(f"{i+1}. {question}")

    command_response = await info_gathering(iu)

    # Create list of coroutines for parallel execution
    finding_tasks = [finding(iu.summary, command) for command in command_response]

    # Execute all findings in parallel
    output_summaries = await asyncio.gather(*finding_tasks)

    outputs = [
        Output(command=command, output_summary=output_summary)
        for command, output_summary in zip(command_response, output_summaries)
    ]

    report = await generate_report(
        iu.summary,
        mode="executor",
        outputs=outputs,
    )
    print(report.content)


# Add this to run the async main function
if __name__ == "__main__":
    asyncio.run(main())
