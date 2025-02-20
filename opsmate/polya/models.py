from pydantic import BaseModel, Field
from typing import List, Optional
import subprocess
from jinja2 import Template
from pydantic import (
    model_validator,
    field_validator,
    ValidationInfo,
    PrivateAttr,
    computed_field,
)
from opsmate.dino import dino
import asyncio
import concurrent.futures
import re


class InitialUnderstandingResponse(BaseModel):
    """
    This is the response format for the summary section.
    """

    summary: str
    questions: List[str]

    @model_validator(mode="after")
    def validate_questions(self, info: ValidationInfo):
        if not info.context:
            return self
        expected_num_questions = info.context.get("num_questions", 3)
        if len(self.questions) != expected_num_questions:
            raise ValueError(
                f"The number of questions must be {expected_num_questions}"
            )
        return self


class NonTechnicalQuery(BaseModel):
    """
    The non-technical query from user
    """

    reason: str = Field(
        description="The reason why this query is not technical related"
    )


@dino("gpt-4o-mini", response_model=bool)
async def command_has_placeholders(command: str) -> bool:
    """
    Check if the command has placeholders

    Example 1:
    command: kubectl -n <namespace> get pods
    return: True

    Example 2:
    command: kubectl -n finance get pods
    return: False

    """
    return command


class Command(BaseModel):
    """
    The command line to be executed
    """

    command: str = Field(description="The command line to be executed")
    description: str = Field(
        description="what are the informations are provided by the command execution"
    )

    _result: str = PrivateAttr()

    @computed_field
    @property
    def result(self) -> str:
        if not hasattr(self, "_result"):
            self._result = self.execute()
        return self._result

    @field_validator("command")
    @classmethod
    def validate_command(cls, v):
        pool = concurrent.futures.ThreadPoolExecutor(1)
        result = pool.submit(asyncio.run, command_has_placeholders(v)).result()
        if result:
            raise ValueError(f"Command {v} has placeholders")
        return v

    def execute(self):
        """
        Execute the command and return the output
        """
        if hasattr(self, "_result"):
            return self._result

        try:
            result = subprocess.run(
                self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self._result = result.stdout
            return result.stdout
        except subprocess.SubprocessError as e:
            self._result = str(e)
            return str(e)


class QuestionResponse(BaseModel):
    """
    The response to the question
    """

    summary: str = Field(
        description="The high level summary of the problem that provides the context"
    )
    question: str = Field(description="The question that is being answered")
    commands: List[Command] = Field(
        description="The command line to be executed to answer the question"
    )

    @model_validator(mode="after")
    def execute_commands(self):
        for command in self.commands:
            command.execute()
        return self

    def __str__(self):
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
{{ command.result }}
```
{% endfor %}
"""
        return Template(jinja_template).render(
            summary=self.summary,
            question=self.question,
            commands=self.commands,
        )


class InfoGathered(BaseModel):
    """
    Information gathered from the command execution
    """

    question: str
    commands: List[Command]
    info_gathered: str = Field(
        description="The information gathered from the command execution in markdown format. MUST NOT contain any markdown headers"
    )

    @model_validator(mode="after")
    def remove_markdown_headers(self):
        self.info_gathered = re.sub(
            r"^#+\s+.*$", "", self.info_gathered, flags=re.MULTILINE
        )
        return self


class Report(BaseModel):
    """
    The detailed report based on the high level summary and the findings
    """

    content: str


class Solution(BaseModel):
    """
    The solution to the problem

    DO NOT use any markdown heading, just use the content as is.
    """

    findings: List[str] = Field(
        description="The list of findings that back the solution"
    )
    solution: str
    probability: int

    def summarize(self, summary: str, show_probability: bool = True):
        template = Template(
            """
### Summary
{{ summary }}
### Findings
{% for finding in findings %}
- {{ finding }}
{% endfor %}
### Solution
{{ solution }}
{% if show_probability %}
### Probability of Success
{{ probability }}
{% endif %}
"""
        )
        return template.render(
            summary=summary,
            findings=self.findings,
            solution=self.solution,
            probability=self.probability,
            show_probability=show_probability,
        )


class ReportExtracted(BaseModel):
    """
    The extracted information from the report

    DO NOT use any markdown heading, just use the content as is.
    """

    summary: str = Field(description="The summary of the problem")
    potential_solutions: List[Solution] = Field(
        description="The potential solutions to the problem, the probabilities of solutions must be added up to 100"
    )

    @model_validator(mode="after")
    def sort_potential_solutions(self):
        self.potential_solutions.sort(key=lambda x: x.probability, reverse=True)
        return self

    @model_validator(mode="after")
    def validate_potential_solutions(self):
        total_probability = sum(
            solution.probability for solution in self.potential_solutions
        )
        if total_probability != 100:
            raise ValueError("The probabilities of solutions must be added up to 100")
        return self

    @model_validator(mode="after")
    def potention_solutions_count(self, info: ValidationInfo):
        if not info.context:
            return self
        max_num_solutions = info.context.get("max_num_solutions", 3)
        if len(self.potential_solutions) > max_num_solutions:
            raise ValueError(
                f"The number of potential solutions must be less than or equal to {max_num_solutions}"
            )
        return self


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

        self.subtasks = sorted
        return sorted


class Fact(BaseModel):
    fact: str = Field(description="Fact that will help to resolve the problem")
    source: str = Field(
        description="The source of the fact, must be a fqdn of the source e.g. https://github.com/jingkaihe/opsmate/blob/main/README.md"
    )
    weight: int = Field(description="Weight of the fact, 1-10")


class Facts(BaseModel):
    facts: list[Fact] = Field(description="Facts that will help to resolve the problem")
