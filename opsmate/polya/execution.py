import instructor
from anthropic import Anthropic
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import List, Union
import subprocess
from jinja2 import Template
from opsmate.polya.models import TaskPlan
from opsmate.polya.planning import planning
from opsmate.polya.understanding import (
    generate_report,
    initial_understanding,
    info_gathering,
)
import asyncio
import tempfile
import yaml


async def execute(task_plan: TaskPlan):
    task_map = {}
    for task in task_plan.subtasks:
        task_map[task.id] = task

    all_task_results = {}

    for task in task_plan.subtasks:
        task_results = []
        for subtask in task.subtasks:
            task_result = all_task_results.get(subtask.id, None)
            if task_result is not None:
                task_results.append(task_result)

        task_result = await task.execute(task_map, task_results)
        all_task_results[task.id] = task_result

    return all_task_results


executor_sys_prompt = """
<assistant>
You are a world classSRE who is good at solving problems. You are specialised in kubernetes and python.
You are tasked to solve the problem by executing python code
</assistant>

<rules>
- Comes up with solutions using python code
- Use stdlib, do not use any third party libraries that needs pip install
- Feel free to shell out to kubectl, helm etc to get the information you need
- Make sure that the stdout and stderr are printed out instead of returned
- Do not hallucinate, only use the information provided in the context
</rules>

<important>
- The script you are executing is mission critical, so make sure it is precise and correct
</important>
"""


class PythonCode(BaseModel):
    """
    The python code to be executed to answer the question
    """

    code: str = Field(description="The python code to be executed")
    description: str = Field(
        description="The description of the python code to be executed"
    )

    async def execute(self):
        # write the code into a tempfile and execute it
        with tempfile.NamedTemporaryFile(suffix=".py") as temp_file:
            temp_file.write(self.code.encode())
            temp_file.flush()
            temp_file_path = temp_file.name

            print(f"Executing code from {temp_file_path}")

            try:
                result = subprocess.run(
                    ["python", temp_file_path],
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                return PythonCodeResult(
                    code=self,
                    result=result.stdout,
                )
            except subprocess.SubprocessError as e:
                return PythonCodeResult(
                    code=self,
                    result=str(e),
                )


class PythonCodeResult(BaseModel):
    code: PythonCode
    result: str


class Execution(BaseModel):
    python_codes: List[PythonCode] = Field(
        description="The python code to be executed to answer the question"
    )


async def main():
    background_context = """
## Summary

The deployment "payment-service" within the "payment" namespace is facing rollout issues due to readiness probe failures. The HTTP endpoint is returning a 404 status code, causing pods to be marked as unhealthy, leading to repeated restarts and delays in deployment, with "ProgressDeadlineExceeded" condition noted.

## Findings


- The readiness probe for the pods is set up to send HTTP requests to a specific endpoint, which is failing with a 404 status code. This suggests that the service or endpoint expected to be up and running is either not available, misconfigured, or incorrectly specified.

## Solution

Verify HTTP Endpoint Configuration. Check and validate the service endpoint that the readiness probe targets. Ensure the route (URL path) and the service is correctly configured to handle requests and is actively running.
"""
    task = "Verify readiness probe configuration in deployment manifest."

    openai = instructor.from_openai(AsyncOpenAI(), mode=instructor.Mode.TOOLS)

    messages = [
        {
            "role": "system",
            "content": executor_sys_prompt,
        },
        {
            "role": "user",
            "content": f"""
<context>
{background_context}
</context>
""",
        },
        {"role": "user", "content": task},
    ]

    execution = await openai.messages.create(
        messages=messages,
        model="gpt-4o",
        response_model=Execution,
    )

    for python_code in execution.python_codes:
        print(python_code.code)
        print(python_code.description)

    result = await asyncio.gather(
        *[python_code.execute() for python_code in execution.python_codes]
    )

    result_template = Template(
        """
<result>
{% for result in results %}
## Execution description

{{ result.code.description }}

## Execution result
```
{{ result.result }}
```
{% endfor %}
</result>
"""
    )

    rendered_result = result_template.render(results=result)
    print(rendered_result)
    messages.append(
        {
            "role": "user",
            "content": f"""
<result>
{rendered_result}
</result>
""",
        }
    )

    messages.append(
        {
            "role": "user",
            "content": "What is the result of the task?",
        }
    )

    response = await openai.messages.create(
        messages=messages,
        model="gpt-4o",
        response_model=str,
    )

    print(response)


if __name__ == "__main__":
    asyncio.run(main())
