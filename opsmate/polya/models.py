from pydantic import BaseModel, Field
from typing import List
import subprocess
from jinja2 import Template


class InitialUnderstandingResponse(BaseModel):
    """
    This is the response format for the summary section.
    """

    summary: str
    questions: List[str]


class NonTechnicalQuery(BaseModel):
    """
    The non-technical query from user
    """

    reason: str = Field(
        description="The reason why this query is not technical related"
    )


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


class QuestionResponseSummary(BaseModel):
    """
    The summary of the question
    """

    question: str
    summary: str


class InfoGathered(BaseModel):
    """
    The summary of the question
    """

    question: str
    commands: List[Command]
    info_gathered: str = Field(
        description="The information gathered from the command execution"
    )


class Report(BaseModel):
    """
    The detailed report based on the high level summary and the findings
    """

    content: str


class Solution(BaseModel):
    """
    The solution to the problem
    """

    findings: List[str] = Field(
        description="The list of findings that back the solution"
    )
    solution: str
    probability: int

    def summarize(self, summary: str, show_probability: bool = True):
        template = Template(
            """
## Summary

{{ summary }}

## Findings

{% for finding in findings %}
- {{ finding }}
{% endfor %}

## Solution

{{ solution }}

{% if show_probability %}
## Probability of Success

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
    """

    summary: str = Field(description="The summary of the problem")
    potential_solutions: List[Solution] = Field(
        description="The potential solutions to the problem"
    )


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
