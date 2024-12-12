from fasthtml.common import *
from sqlmodel import Session
from pydantic import BaseModel
from opsmate.gui.assets import *
from opsmate.gui.models import (
    Cell,
    CellLangEnum,
    WorkflowEnum,
    BluePrint,
    Workflow,
    executor,
    k8s_agent,
    ThinkingSystemEnum,
)
from opsmate.libs.core.types import (
    ExecResults,
    Observation,
    ReactProcess,
    ReactAnswer,
    Agent,
)
from opsmate.libs.core.engine.agent_executor import AgentCommand
from opsmate.polya.models import (
    InitialUnderstandingResponse,
    InfoGathered,
    NonTechnicalQuery,
    Report,
    TaskPlan,
    Solution,
    ReportExtracted,
)

from opsmate.polya.understanding import (
    initial_understanding,
    info_gathering,
    generate_report,
    report_breakdown,
)
from opsmate.polya.planning import planning
import pickle
import sqlmodel
import structlog
import asyncio
import subprocess
from jinja2 import Template
import json

logger = structlog.get_logger()

# Set up the app, including daisyui and tailwind for the chat component
tlink = (Script(src="https://cdn.tailwindcss.com"),)
nav = (
    Nav(
        Div(
            A("Opsmate Workspace", cls="btn btn-ghost text-xl", href="/"),
            A("Freestyle", href="/blueprint/freestyle", cls="btn btn-ghost text-sm"),
            cls="flex-1",
        ),
        Div(
            Label(
                Input(
                    type="checkbox",
                    value="synthwave",
                    cls="theme-controller",
                    hidden=true,
                ),
                sun_icon_svg,
                moon_icon_svg,
                cls="swap swap-rotate",
            ),
        ),
        cls="navbar bg-base-100 shadow-lg mb-4 fixed top-0 left-0 right-0 z-50",
    ),
)

dlink = Link(
    rel="stylesheet",
    href="https://cdn.jsdelivr.net/npm/daisyui@4.11.1/dist/full.min.css",
)


def cell_output(cell: Cell):
    if cell.output:
        outputs = pickle.loads(cell.output)
        outputs = [
            cell_render_funcs[output["type"]](k8s_agent.metadata.name, output["output"])
            for output in outputs
        ]
    else:
        outputs = []
    return Div(
        Span(f"Out [{cell.execution_sequence}]:", cls="text-gray-500 text-sm"),
        Div(
            *outputs,
            id=f"cell-output-{cell.id}",
        ),
        cls="px-4 py-2 bg-gray-50 border-t rounded-b-lg overflow-hidden",
    )


def cell_component(cell: Cell, cell_size: int):
    """Renders a single cell component"""
    # Determine if the cell is active
    active_class = "border-green-500 bg-white" if cell.active else "border-gray-300"

    return Div(
        # Add Cell Button Menu
        cell_insert_dropdown(cell),
        # Main Cell Content
        Div(
            # Cell Header
            cell_header(cell, cell_size),
            # Cell Input - Updated with conditional styling
            cell_input_form(cell),
            # Cell Output (if any)
            cell_output(cell),
            cls=f"rounded-lg shadow-sm border {active_class}",  # Apply the active class here
        ),
        cls="group relative",
        key=cell.id,
        id=f"cell-component-{cell.id}",
    )


def add_cell_button(blueprint: BluePrint):
    return (
        Div(
            Button(
                add_cell_svg,
                "Add Cell",
                hx_post=f"/blueprint/{blueprint.id}/cell/bottom",
                cls="btn btn-primary btn-sm flex items-center gap-2",
            ),
            id="add-cell-button",
            hx_swap_oob="true",
            cls="flex justify-end",
        ),
    )


def reset_button(blueprint: BluePrint):
    return (
        Div(
            Button(
                "Reset",
                cls="btn btn-secondary btn-sm flex items-center gap-1",
            ),
            hx_post=f"/blueprint/{blueprint.id}/cells/reset",
            hx_swap_oob="true",
            id="reset-button",
            cls="flex",
        ),
    )


def cell_header(cell: Cell, cell_size: int):
    blueprint = cell.workflow.blueprint
    return (
        Div(
            Div(
                Span(f"In [{cell.execution_sequence}]:", cls="text-gray-500 text-sm"),
                # Add cell type selector
                cls="flex items-center gap-2",
            ),
            Div(
                Select(
                    Option(
                        "Text Instruction",
                        value=CellLangEnum.TEXT_INSTRUCTION.value,
                        selected=cell.lang == CellLangEnum.TEXT_INSTRUCTION,
                    ),
                    Option(
                        "Bash",
                        value=CellLangEnum.BASH.value,
                        selected=cell.lang == CellLangEnum.BASH,
                    ),
                    name="lang",
                    hx_put=f"/blueprint/{blueprint.id}/cell/{cell.id}",
                    hx_trigger="change",
                    cls="select select-sm ml-2",
                ),
                Select(
                    Option(
                        "Type 1 - Fast",
                        value=ThinkingSystemEnum.TYPE1.value,
                        selected=cell.thinking_system == ThinkingSystemEnum.TYPE1
                        or cell.lang == CellLangEnum.BASH,
                    ),
                    Option(
                        "Type 2 - Slow but thorough",
                        value=ThinkingSystemEnum.TYPE2.value,
                        selected=cell.thinking_system == ThinkingSystemEnum.TYPE2,
                    ),
                    name="thinking_system",
                    hx_put=f"/blueprint/{blueprint.id}/cell/{cell.id}",
                    hx_trigger="change",
                    cls="select select-sm ml-2 min-w-[240px]",
                    hidden=cell.lang == CellLangEnum.BASH,
                ),
                Button(
                    trash_icon_svg,
                    hx_delete=f"/blueprint/{blueprint.id}/cell/{cell.id}",
                    cls="btn btn-ghost btn-sm opacity-0 group-hover:opacity-100 hover:text-red-500",
                    disabled=cell_size == 1,
                ),
                Form(
                    Input(type="hidden", value=cell.id, name="cell_id"),
                    Button(
                        run_icon_svg,
                        cls="btn btn-ghost btn-sm",
                    ),
                    ws_connect=f"/cell/run/ws/",
                    ws_send=True,
                    hx_ext="ws",
                ),
                cls="ml-auto flex items-center gap-2",
            ),
            id=f"cell-header-{cell.id}",
            cls="flex items-center px-4 py-2 bg-gray-100 border-b justify-between rounded-t-lg overflow-hidden",
        ),
    )


def cell_insert_dropdown(cell: Cell):
    blueprint = cell.workflow.blueprint
    return (
        Div(
            Div(
                Button(
                    plus_icon_svg,
                    tabindex="0",
                    cls="btn btn-ghost btn-xs",
                ),
                Ul(
                    Li(
                        Button(
                            "Insert Above",
                            hx_post=f"/blueprint/{blueprint.id}/cell/{cell.id}?above=true",
                        )
                    ),
                    Li(
                        Button(
                            "Insert Below",
                            hx_post=f"/blueprint/{blueprint.id}/cell/{cell.id}?above=false",
                        )
                    ),
                    tabindex="0",
                    cls="dropdown-content z-10 menu p-2 shadow bg-base-100 rounded-box",
                ),
                cls="dropdown dropdown-right",
            ),
            cls="absolute -left-8 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity",
        ),
    )


def cell_input_form(cell: Cell):
    blueprint = cell.workflow.blueprint
    return (
        Div(
            Form(
                Textarea(
                    cell.input,
                    name="input",
                    cls=f"w-full h-24 p-2 font-mono text-sm border rounded focus:outline-none focus:border-blue-500",
                    placeholder="Enter your instruction here...",
                    id=f"cell-input-{cell.id}",
                ),
                Div(
                    hx_put=f"/blueprint/{blueprint.id}/cell/input/{cell.id}",
                    hx_trigger=f"keyup[!(shiftKey&&keyCode===13)] changed delay:500ms from:#cell-input-{cell.id}",
                    hx_swap=f"#cell-input-form-{cell.id}",
                ),
                # xxx: shift+enter is being registered as a newline
                Div(
                    Input(type="hidden", value=cell.id, name="cell_id"),
                    ws_connect=f"/cell/run/ws/",
                    ws_send=True,
                    hx_ext="ws",
                    hx_trigger=f"keydown[shiftKey&&keyCode===13] from:#cell-input-{cell.id}",
                    hx_swap=f"#cell-input-form-{cell.id}",
                ),
                id=f"cell-input-form-{cell.id}",
            ),
            hx_include="input",
            cls="p-4",
        ),
    )


def workflow_button(workflow: Workflow):
    cls = "px-6 py-3 text-sm font-medium border-0"
    if workflow.active:
        cls += " bg-white border-b-2 border-b-blue-500 text-blue-600"
    else:
        cls += " bg-gray-50 text-gray-600 hover:bg-gray-100"
    return Button(
        workflow.title,
        hx_put=f"/workflow/{workflow.id}/switch",
        cls=cls,
    )


def marshal_output(output: dict | BaseModel | str):
    if isinstance(output, BaseModel):
        return output.model_dump()
    elif isinstance(output, str):
        return output
    elif isinstance(output, dict):
        for k, v in output.items():
            output[k] = marshal_output(v)
        return output


async def prefill_conversation(cell: Cell, agent: Agent, session: sqlmodel.Session):
    executor.clear_history(agent)
    agent.status.historical_context = []

    workflow = cell.workflow
    previous_cells = workflow.find_previous_cells(session, cell)

    for idx, previous_cell in enumerate(previous_cells):
        assistant_response = ""
        for output in pickle.loads(previous_cell.output):
            o = output["output"]
            marshalled_output = marshal_output(o)
            if isinstance(marshalled_output, dict):
                assistant_response += json.dumps(marshalled_output, indent=2) + "\n"
            else:
                assistant_response += marshalled_output + "\n"

        conversation = f"""
Conversation {idx + 1}:

<user instruction>
{previous_cell.input}
</user instruction>

<assistant response>
{assistant_response}
</assistant response>
"""
        agent.status.historical_context.append(
            Observation(action="", observation=conversation)
        )


async def execute_llm_react_instruction(
    cell: Cell, swap: str, send, session: sqlmodel.Session
):

    logger.info("executing llm react instruction", cell_id=cell.id)

    await prefill_conversation(cell, k8s_agent, session)

    outputs = []
    await send(
        Div(
            *outputs,
            hx_swap_oob="true",
            id=f"cell-output-{cell.id}",
        )
    )
    msg = cell.input.rstrip()
    # execution = executor.supervise(supervisor, msg)
    execution = executor.execute(k8s_agent, msg)

    async for stage in async_wrapper(execution):
        actor = k8s_agent.metadata.name
        output = stage
        partial = None
        if isinstance(output, ExecResults):
            partial = render_exec_results_markdown(actor, output)
        elif isinstance(output, AgentCommand):
            partial = render_agent_command_markdown(actor, output)
        elif isinstance(output, ReactProcess):
            partial = render_react_markdown(actor, output)
        elif isinstance(output, ReactAnswer):
            partial = render_react_answer_markdown(actor, output)
        # elif isinstance(output, Observation):
        #     partial = render_observation_markdown(actor, output)
        if partial:
            outputs.append(
                {
                    "type": type(output).__name__,
                    "output": output,
                }
            )
            await send(
                Div(
                    partial,
                    hx_swap_oob=swap,
                    id=f"cell-output-{cell.id}",
                )
            )

    cell.output = pickle.dumps(outputs)
    session.add(cell)
    session.commit()


async def execute_llm_type2_instruction(
    cell: Cell, swap: str, send, session: sqlmodel.Session
):
    workflow = cell.workflow
    if workflow.name == WorkflowEnum.UNDERSTANDING:
        return await execute_polya_understanding_instruction(cell, swap, send, session)
    elif workflow.name == WorkflowEnum.PLANNING:
        return await execute_polya_planning_instruction(cell, swap, send, session)
    elif workflow.name == WorkflowEnum.EXECUTION:
        return await execute_polya_execution_instruction(cell, swap, send, session)


async def execute_polya_understanding_instruction(
    cell: Cell, swap: str, send, session: sqlmodel.Session
):
    msg = cell.input.rstrip()
    logger.info("executing polya understanding instruction", cell_id=cell.id, input=msg)

    outputs = []
    await send(
        Div(
            *outputs,
            hx_swap_oob="true",
            id=f"cell-output-{cell.id}",
        )
    )

    iu = await initial_understanding(msg)
    if isinstance(iu, NonTechnicalQuery):
        outputs.append(
            {
                "type": "NonTechnicalQuery",
                "output": NonTechnicalQuery(**iu.model_dump()),
            }
        )
        await send(
            Div(
                UnderstandingRenderer.render_non_technical_query_markdown(
                    k8s_agent.metadata.name, iu
                ),
                hx_swap_oob=swap,
                id=f"cell-output-{cell.id}",
            )
        )
        cell.output = pickle.dumps(outputs)
        session.add(cell)
        session.commit()
        return

    outputs.append(
        {
            "type": "InitialUnderstanding",
            "output": InitialUnderstandingResponse(**iu.model_dump()),
        }
    )
    await send(
        Div(
            UnderstandingRenderer.render_initial_understanding_markdown(
                k8s_agent.metadata.name, iu
            ),
            hx_swap_oob=swap,
            id=f"cell-output-{cell.id}",
        )
    )

    finding_tasks = [info_gathering(iu.summary, question) for question in iu.questions]

    infos_gathered = []
    for i, task in enumerate(finding_tasks):
        info_gathered = await task
        # output = Output(
        #     command=commands[i],
        #     output_summary=OutputSummary(summary=output_summary.summary),
        # )
        info_gathered = InfoGathered(**info_gathered.model_dump())
        outputs.append(
            {
                "type": "InfoGathered",
                "output": info_gathered,
            }
        )
        infos_gathered.append(info_gathered)
        await send(
            Div(
                UnderstandingRenderer.render_info_gathered_markdown(
                    k8s_agent.metadata.name, info_gathered
                ),
                hx_swap_oob=swap,
                id=f"cell-output-{cell.id}",
            )
        )

    report = await generate_report(
        iu.summary, mode="executor", info_gathered=infos_gathered
    )
    report_extracted = await report_breakdown(report)
    for solution in report_extracted.potential_solutions:
        output = {
            "summary": report_extracted.summary,
            "solution": Solution(**solution.model_dump()),
        }
        outputs.append(
            {
                "type": "PotentialSolution",
                "output": output,
            }
        )
        await send(
            Div(
                UnderstandingRenderer.render_potential_solution_markdown(
                    k8s_agent.metadata.name, output
                ),
                hx_swap_oob=swap,
                id=f"cell-output-{cell.id}",
            )
        )

    cell.output = pickle.dumps(outputs)
    session.add(cell)
    session.commit()

    workflow = cell.workflow
    workflow.result = report_extracted.model_dump_json()
    session.add(workflow)
    session.commit()


async def execute_polya_planning_instruction(
    cell: Cell, swap: str, send, session: sqlmodel.Session
):
    msg = cell.input.rstrip()
    logger.info("executing polya understanding instruction", cell_id=cell.id, input=msg)

    blueprint = cell.workflow.blueprint
    understanding_workflow: Workflow = blueprint.find_workflow_by_name(
        session, WorkflowEnum.UNDERSTANDING
    )
    report_extracted_json = understanding_workflow.result

    # pick the most optimal solution
    report_extracted = ReportExtracted.model_validate_json(report_extracted_json)
    solution = report_extracted.potential_solutions[0]
    summary = report_extracted.summary

    outputs = []
    await send(
        Div(
            *outputs,
            hx_swap_oob="true",
            id=f"cell-output-{cell.id}",
        )
    )

    task_plan = await planning(msg, solution.summarize(summary))
    outputs.append(
        {
            "type": "TaskPlan",
            "output": TaskPlan(**task_plan.model_dump()),
        }
    )

    await send(
        Div(
            render_task_plan_markdown(k8s_agent.metadata.name, task_plan),
            hx_swap_oob=swap,
            id=f"cell-output-{cell.id}",
        )
    )

    cell.output = pickle.dumps(outputs)
    session.add(cell)
    session.commit()

    workflow = cell.workflow
    workflow.result = task_plan.model_dump_json()
    session.add(workflow)
    session.commit()


async def execute_polya_execution_instruction(
    cell: Cell, swap: str, send, session: sqlmodel.Session
):
    msg = cell.input.rstrip()
    logger.info("executing polya execution instruction", cell_id=cell.id, input=msg)

    blueprint = cell.workflow.blueprint
    understanding_workflow: Workflow = blueprint.find_workflow_by_name(
        session, WorkflowEnum.UNDERSTANDING
    )
    report_extracted_json = understanding_workflow.result
    report_extracted = ReportExtracted.model_validate_json(report_extracted_json)

    solution_summary = report_extracted.potential_solutions[0].summarize(
        report_extracted.summary, show_probability=False
    )

    print(solution_summary)

    planning_workflow: Workflow = blueprint.find_workflow_by_name(
        session, WorkflowEnum.PLANNING
    )
    task_plan_json = planning_workflow.result

    task_plan = TaskPlan.model_validate_json(task_plan_json)

    print(task_plan.model_dump_json(indent=2))


async def execute_bash_instruction(
    cell: Cell, swap: str, send, session: sqlmodel.Session
):
    logger.info("executing bash instruction", cell_id=cell.id)
    outputs = []
    await send(
        Div(
            *outputs,
            hx_swap_oob="true",
            id=f"cell-output-{cell.id}",
        )
    )

    script = cell.input.rstrip()
    # execute the script using subprocess with combined output
    process = subprocess.Popen(
        script,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1,
    )

    combined_output = ""
    while True:
        output = process.stdout.readline()
        error = process.stderr.readline()

        if output == "" and error == "" and process.poll() is not None:
            break

        if output:
            combined_output += output
        if error:
            combined_output += error

    partial = render_bash_output_markdown(k8s_agent.metadata.name, combined_output)
    outputs.append(
        {
            "type": "BashOutput",
            "output": combined_output,
        }
    )
    cell.output = pickle.dumps(outputs)
    session.add(cell)
    session.commit()
    await send(
        Div(
            partial,
            hx_swap_oob=swap,
            id=f"cell-output-{cell.id}",
        )
    )


def home_body(db_session: Session, session_name: str, blueprint: BluePrint):
    active_workflow = blueprint.active_workflow(db_session)
    workflows = blueprint.workflows
    cells = active_workflow.cells
    return Body(
        Div(
            Card(
                # Header
                Div(
                    Div(
                        H1(session_name, cls="text-2xl font-bold"),
                        Span(
                            "Press Shift+Enter to run cell",
                            cls="text-sm text-gray-500",
                        ),
                        cls="flex flex-col",
                    ),
                    Div(
                        reset_button(blueprint),
                        add_cell_button(blueprint),
                        cls="flex gap-2 justify-start",
                    ),
                    cls="mb-4 flex justify-between items-start pt-16",
                ),
                render_workflow_panel(workflows, active_workflow),
                # Cells Container
                render_cell_container(cells),
                # cls="overflow-hidden",
            ),
            cls="max-w-6xl mx-auto p-4 bg-gray-50 min-h-screen",
        )
    )


async def async_wrapper(generator: Generator):
    for stage in generator:
        await asyncio.sleep(0)
        yield stage


def render_cell_container(cells: list[Cell], hx_swap_oob: str = None):
    div = Div(
        *[cell_component(cell, len(cells)) for cell in cells],
        cls="space-y-4 mt-4",
        id="cells-container",
    )
    if hx_swap_oob:
        div.hx_swap_oob = hx_swap_oob
    return div


def render_workflow_panel(workflows: list[Workflow], active_workflow: Workflow):
    return Div(
        Div(
            *[workflow_button(workflow) for workflow in workflows],
            cls="flex border-t",
        ),
        # workflow Panels
        Div(
            Div(
                Div(
                    Span(
                        f"Current Phase: {active_workflow.title}",
                        cls="font-medium",
                    ),
                    cls="flex items-center gap-2 text-sm text-gray-500",
                ),
                cls="space-y-6",
            ),
            cls="block p-4",
        ),
        # workflow description
        Div(
            Div(
                Div(
                    active_workflow.description,
                    cls="text-sm text-gray-700 marked",
                ),
                cls="flex items-center gap-2",
            ),
            cls="bg-blue-50 p-4 rounded-lg border border-blue-100",
        ),
        hx_swap_oob="true",
        id="workflow-panel",
    )


def render_react_markdown(agent: str, output: ReactProcess):
    return Div(
        f"""
**{agent} thought process**

| Thought | Action |
| --- | --- |
| {output.thought} | {output.action} |
""",
        cls="marked",
    )


def render_react_answer_markdown(agent: str, output: ReactAnswer):
    return Div(
        f"""
**{agent} answer**

{output.answer}
""",
        cls="marked",
    )


def render_agent_command_markdown(agent: str, output: AgentCommand):
    return Div(
        f"""
**{agent} task delegation**

{output.instruction}

<br>
""",
        cls="marked",
    )


def render_observation_markdown(agent: str, output: Observation):
    return Div(
        f"""
**{agent} observation**

{output.observation}
""",
        cls="marked",
    )


def render_exec_results_markdown(agent: str, output: ExecResults):
    markdown_outputs = []
    markdown_outputs.append(
        Div(
            f"""
**{agent} results**
""",
            cls="marked",
        )
    )
    for result in output.results:
        output = ""
        column_names = result.table_column_names()
        columns = result.table_columns()

        for idx, column in enumerate(columns):
            output += f"""
**{column_names[idx][0]}**

```
{column}
```
---

"""

        markdown_outputs.append(Div(output, cls="marked"))
    return Div(*markdown_outputs)


def render_bash_output_markdown(agent: str, output: str):
    return Div(
        f"""
**{agent} results**

```bash
{output}
```
""",
        cls="marked",
    )


def render_task_plan_markdown(agent: str, task_plan: TaskPlan):
    return Div(
        f"""
**{agent} task plan**

## Goal

{task_plan.goal}

## Subtasks

{"\n".join([f"* {subtask.task}" for subtask in task_plan.subtasks])}
""",
        cls="marked",
    )


class UnderstandingRenderer:
    @staticmethod
    def render_initial_understanding_markdown(
        agent: str, iu: InitialUnderstandingResponse
    ):
        return Div(
            f"""
**Initial understanding**

{iu.summary}

{ "**Questions**" if iu.questions else "" }
{"\n".join([f"{i+1}. {question}" for i, question in enumerate(iu.questions)])}
""",
            cls="marked",
        )

    @staticmethod
    def render_info_gathered_markdown(agent: str, info_gathered: InfoGathered):
        template = """
**Information Gathering**

**Question:**

{{ info_gathered.question }}

**Command:**

{% for command in info_gathered.commands %}
```
# {{ command.description }}
{{ command.command }}
```
{% endfor %}

**Summary:**

> {{ info_gathered.info_gathered }}

"""

        return Div(
            Template(template).render(info_gathered=info_gathered),
            cls="marked",
        )

    @staticmethod
    def render_potential_solution_markdown(agent: str, output: dict):
        summary = output.get("summary", "")
        solution = output.get("solution", {})

        rendered = solution.summarize(summary)
        return Div(
            f"""
```
{rendered}
```
""",
            cls="marked",
        )

    @staticmethod
    def render_non_technical_query_markdown(
        agent: str, non_technical_query: NonTechnicalQuery
    ):
        return Div(
            f"""
This is a non-technical query, thus I don't know how to answer it.

**Reason:** {non_technical_query.reason}
""",
            cls="marked",
        )


cell_render_funcs = {
    "ReactProcess": render_react_markdown,
    "AgentCommand": render_agent_command_markdown,
    "ReactAnswer": render_react_answer_markdown,
    "Observation": render_observation_markdown,
    "ExecResults": render_exec_results_markdown,
    "BashOutput": render_bash_output_markdown,
    "InitialUnderstanding": UnderstandingRenderer.render_initial_understanding_markdown,
    "InfoGathered": UnderstandingRenderer.render_info_gathered_markdown,
    "PotentialSolution": UnderstandingRenderer.render_potential_solution_markdown,
    "NonTechnicalQuery": UnderstandingRenderer.render_non_technical_query_markdown,
    "TaskPlan": render_task_plan_markdown,
}
