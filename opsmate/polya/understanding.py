from opsmate.polya.models import (
    QuestionResponse,
    InfoGathered,
    Report,
    InitialUnderstandingResponse,
    NonTechnicalQuery,
    ReportExtracted,
)
from typing import List, Union, Any
from jinja2 import Template
import asyncio
from opsmate.dino import dino
from opsmate.dino.types import Message, ListOfMessageOrDict
from instructor import AsyncInstructor

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


@dino(
    "claude-3-5-sonnet-20241022",
    response_model=Union[InitialUnderstandingResponse, NonTechnicalQuery],
    context={"num_questions": 3},
)
async def initial_understanding(
    query: str,
    prefill: str = extra_sys_prompt,
    context: dict[str, Any] = {"num_questions": 3},
    chat_history: ListOfMessageOrDict = [],
):
    """
    <assistant>
    You are a world class SRE who is good at solving problems. You are tasked to summarise the problem and ask clarifying questions.
    </assistant>

    <rules>
    You will receive a user query that may include a problem description, command line output, logs as the context.
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
    - Use markdown in your response.
    - Feel free to leave the questions blank if you think you have enough information to solve the problem.
    </important_notes>
    """
    return [
        Message.system(prefill),
        *Message.normalise(chat_history),
        Message.user(f"Please ask {context['num_questions']} questions at most"),
        Message.user(query),
    ]


@dino(
    "claude-3-5-sonnet-20241022",
    response_model=InitialUnderstandingResponse,
)
async def load_inital_understanding(text: str):
    """
    You are a world class information extractor. You are good at extracting information from a text.
    Please be accurate with the number of questions in the text given based on the markdown bullet points.
    """
    return [
        Message.user(text),
    ]


@dino(
    "claude-3-5-sonnet-20241022",
    response_model=QuestionResponse,
)
async def __info_gathering(
    summary: str, question: str, context: str = extra_sys_prompt
):
    """
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
    return [
        Message.system(context),
        Message.user(f"<summary>{summary}</summary>"),
        Message.user(f"<question>{question}</question>"),
    ]


@dino("claude-3-5-sonnet-20241022", response_model=str)
async def __summarise_info_gathered(question: QuestionResponse):
    """
    You are a world class SRE.
    You are given a question. In respond with a list of commands and the execution output.
    Please provide a short summary based on the question and command execution output in 100 words or less in markdown format.
    """
    return str(question)


async def info_gathering(
    summary: str, question: str, model: str = None, client: AsyncInstructor = None
):
    question_response = await __info_gathering(
        summary, question, model=model, client=client
    )
    summarised_info = await __summarise_info_gathered(
        question_response, model=model, client=client
    )
    return InfoGathered(
        question=question_response.question,
        commands=question_response.commands,
        info_gathered=summarised_info,
    )


@dino("claude-3-5-sonnet-20241022", response_model=Report)
async def generate_report(
    summary: str,
    info_gathered: List[InfoGathered],
):
    """
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
    - **ONLY** list potential solutions that are relevant to the problem.
    - Feel free to just to list 1 potential solution if you are 100% sure that it is the solution.
    - The sum of probability of all potential solutions should be added up to 100%
    </important_notes>
    """

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

    return Template(template).render(summary=summary, info_gathered=info_gathered)


@dino(
    "claude-3-5-sonnet-20241022",
    response_model=ReportExtracted,
    context={"max_num_solutions": 3},
)
async def report_breakdown(
    report: Report, context: dict[str, Any] = {"max_num_solutions": 3}
):
    """
    Break down the report into a structured format
    """
    return report.content


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
        info_gathered=info_gathered,
    )
    print(report.content)


# Add this to run the async main function
if __name__ == "__main__":
    asyncio.run(main())
