from fasthtml.common import *
from sqlmodel import Session
from opsmate.gui.assets import *
from opsmate.gui.models import (
    Cell,
    WorkflowEnum,
    BluePrint,
    Workflow,
    CellType,
    gen_k8s_react,
    conversation_context,
    CellLangEnum,
    ThinkingSystemEnum,
    CreatedByType,
    CellStateEnum,
)
from opsmate.gui.components import (
    CellComponent,
    CellOutputRenderer,
    render_observation_markdown_raw,
    render_react_markdown_raw,
    render_react_answer_markdown_raw,
)
from opsmate.dino.types import Message, Observation, React, ReactAnswer

from opsmate.polya.models import (
    TaskPlan,
    ReportExtracted,
    Facts,
)
from opsmate.tools.system import SysChdir

from sqlmodel import select


from opsmate.polya.execution import iac_sme
import pickle
import sqlmodel
import structlog
import subprocess
import json
from opsmate.workflow.workflow import (
    WorkflowContext,
    WorkflowExecutor,
    build_workflow,
    cond,
)
from opsmate.workflow.workflow import (
    WorkflowStep as OpsmateWorkflowStep,
)
from opsmate.gui.models import Config
from opsmate.gui.steps import (
    manage_initial_understanding_cell,
    cond_is_technical_query,
    manage_info_gather_cells,
    generate_report_with_breakdown,
    manage_potential_solution_cells,
    store_report_extracted,
    manage_planning_optimial_solution_cell,
    manage_planning_knowledge_retrieval_cell,
    manage_planning_task_plan_cell,
    store_facts_and_plans,
)
import yaml
from typing import AsyncGenerator

logger = structlog.get_logger()

config = Config()

k8s_react = gen_k8s_react(config)

# Set up the app, including daisyui and tailwind for the chat component
tlink = Script(src="https://cdn.tailwindcss.com?plugins=typography")
dlink = Link(
    rel="stylesheet",
    href="https://cdn.jsdelivr.net/npm/daisyui@4.11.1/dist/full.min.css",
)

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


async def prefill_conversation(cell: Cell, session: Session):
    chat_history = []
    for conversation in conversation_context(cell, session):
        chat_history.append(Message.user(conversation))
    return chat_history


async def new_react_cell(
    output: React | ReactAnswer | Observation,
    prev_cell: Cell,
    session: Session,
    send,
):
    workflow = prev_cell.workflow
    match output:
        case React():
            input = render_react_markdown_raw(output)
            cell_output = {
                "type": "React",
                "output": output,
            }
            thinking_system = CellType.REASONING_THOUGHTS
        case ReactAnswer():
            input = render_react_answer_markdown_raw(output)
            cell_output = {
                "type": "ReactAnswer",
                "output": output,
            }
            thinking_system = CellType.REASONING_ANSWER
        case Observation():
            input = render_observation_markdown_raw(output)
            cell_output = {
                "type": "Observation",
                "output": Observation(
                    tool_outputs=[
                        output.__class__(**output.model_dump())
                        for output in output.tool_outputs
                    ],
                    observation=output.observation,
                ),
            }
            thinking_system = CellType.REASONING_OBSERVATION
        case _:
            logger.error("unknown output type", output=output)
            return
    react_cell = Cell(
        input=input,
        output=pickle.dumps([cell_output]),
        lang=CellLangEnum.TEXT_INSTRUCTION,
        thinking_system=ThinkingSystemEnum.REASONING,
        state=CellStateEnum.COMPLETED,
        sequence=prev_cell.sequence + 1,
        execution_sequence=prev_cell.execution_sequence + 1,
        active=True,
        workflow_id=prev_cell.workflow_id,
        parent_cell_ids=[prev_cell.id],
        cell_type=thinking_system,
        created_by=CreatedByType.ASSISTANT,
        hidden=True,
    )
    session.add(react_cell)
    session.commit()

    workflow.activate_cell(session, react_cell.id)
    session.commit()

    await send(
        Div(
            CellComponent(react_cell),
            hx_swap_oob="beforeend",
            id="cells-container",
        )
    )

    return react_cell


async def render_notes_output(
    cell: Cell,
    session: Session,
    send,
    cell_state: CellStateEnum | None = None,
):
    cell_output = {
        "type": "NotesOutput",
        "output": cell.input,
    }
    msg = cell.input.rstrip()
    cell.input = msg
    cell.output = pickle.dumps([cell_output])
    cell.hidden = True

    if cell_state:
        cell.state = cell_state

    session.add(cell)
    session.commit()

    await send(
        Div(
            CellComponent(cell),
            hx_swap_oob="true",
            id=f"cell-component-{cell.id}",
        )
    )
    return cell


async def react_streaming(
    cell: Cell,
    swap: str,
    send,
    session: Session,
    reactGenerator: AsyncGenerator[React, None],
):
    prev_cell = cell
    thought_deduped = False
    stopped = False
    async for output in await reactGenerator:
        logger.info("output", output=output)
        session.refresh(cell)

        if cell.state == CellStateEnum.STOPPING:
            logger.info("reasoning is stopping", cell_id=cell.id)
            cell.state = CellStateEnum.STOPPED
            session.add(cell)
            session.commit()
            logger.info("reasoning stopped", cell_id=cell.id)
            stopped = True
            break

        if cell.cell_type == CellType.REASONING_THOUGHTS and not thought_deduped:
            logger.info("thought deduped", output=output)
            cell.input = render_react_markdown_raw(output)
            cell = await render_notes_output(
                cell, session, send, cell_state=CellStateEnum.COMPLETED
            )
            prev_cell = cell
            thought_deduped = True
        else:
            prev_cell = await new_react_cell(output, prev_cell, session, send)

    if not stopped:
        cell = await render_notes_output(
            cell, session, send, cell_state=CellStateEnum.COMPLETED
        )


async def execute_llm_react_instruction(cell: Cell, swap: str, send, session: Session):

    logger.info("executing llm react instruction", cell_id=cell.id)

    chat_history = await prefill_conversation(cell, session)

    cell = await render_notes_output(
        cell, session, send, cell_state=CellStateEnum.RUNNING
    )
    logger.info("chat_history", chat_history=chat_history)

    await react_streaming(
        cell, swap, send, session, k8s_react(cell.input, chat_history=chat_history)
    )


async def execute_llm_simple_instruction(cell: Cell, swap: str, send, session: Session):
    logger.info("executing llm simple instruction", cell_id=cell.id)

    cell = await render_notes_output(
        cell, session, send, cell_state=CellStateEnum.COMPLETED
    )


async def execute_llm_type2_instruction(cell: Cell, swap: str, send, session: Session):
    workflow = cell.workflow
    if workflow.name == WorkflowEnum.UNDERSTANDING:
        if cell.cell_type == CellType.UNDERSTANDING_ASK_QUESTIONS:
            return await update_initial_understanding(cell, send, session)
        elif cell.cell_type == CellType.UNDERSTANDING_GATHER_INFO:
            return await update_info_gathering(cell, send, session)
        else:
            return await execute_polya_understanding_instruction(cell, send, session)
    elif workflow.name == WorkflowEnum.PLANNING:
        if cell.cell_type == CellType.PLANNING_OPTIMAL_SOLUTION:
            return await update_planning_optimial_solution(cell, send, session)
        elif cell.cell_type == CellType.PLANNING_KNOWLEDGE_RETRIEVAL:
            return await update_planning_knowledge_retrieval(cell, swap, send, session)
        elif cell.cell_type == CellType.PLANNING_TASK_PLAN:
            return await update_planning_task_plan(cell, swap, send, session)
        else:
            return await execute_polya_planning_instruction(cell, swap, send, session)
    elif workflow.name == WorkflowEnum.EXECUTION:
        return await execute_polya_execution_instruction(cell, swap, send, session)


async def execute_polya_understanding_instruction(cell: Cell, send, session: Session):
    msg = cell.input.rstrip()
    logger.info("executing polya understanding instruction", cell_id=cell.id, input=msg)

    await render_notes_output(cell, session, send, cell_state=CellStateEnum.RUNNING)

    blueprint = manage_initial_understanding_cell >> cond(
        cond_is_technical_query,
        left=(
            reduce(lambda x, y: x | y, manage_info_gather_cells)
            >> generate_report_with_breakdown
            >> reduce(lambda x, y: x | y, manage_potential_solution_cells)
            >> store_report_extracted
        ),
    )

    opsmate_workflow = build_workflow(
        "understanding",
        "Understand the problem",
        blueprint,
        session,
    )
    executor = WorkflowExecutor(opsmate_workflow, session)
    ctx = WorkflowContext(
        input={"session": session, "question_cell": cell, "send": send}
    )

    await executor.run(ctx)

    await render_notes_output(cell, session, send, cell_state=CellStateEnum.COMPLETED)


async def update_initial_understanding(
    cell: Cell,
    send,
    session: Session,
):
    opsmate_workflow_step = session.exec(
        select(OpsmateWorkflowStep)
        .where(OpsmateWorkflowStep.id == cell.internal_workflow_step_id)
        .where(OpsmateWorkflowStep.workflow_id == cell.internal_workflow_id)
    ).first()
    if not opsmate_workflow_step:
        logger.error("Opsmate workflow step not found", cell_id=cell.id)
        return
    opsmate_workflow = opsmate_workflow_step.workflow

    executor = WorkflowExecutor(opsmate_workflow, session)
    await executor.mark_rerun(opsmate_workflow_step)

    await executor.run(
        WorkflowContext(
            input={
                "session": session,
                "question_cell": cell.parent_cells(session)[0],
                "current_iu_cell": cell,
                "send": send,
            }
        )
    )


async def update_info_gathering(
    cell: Cell,
    send,
    session: Session,
):

    opsmate_workflow_step = session.exec(
        select(OpsmateWorkflowStep)
        .where(OpsmateWorkflowStep.id == cell.internal_workflow_step_id)
        .where(OpsmateWorkflowStep.workflow_id == cell.internal_workflow_id)
    ).first()
    if not opsmate_workflow_step:
        logger.error("Opsmate workflow step not found", cell_id=cell.id)
        return
    opsmate_workflow = opsmate_workflow_step.workflow

    executor = WorkflowExecutor(opsmate_workflow, session)
    await executor.mark_rerun(opsmate_workflow_step)

    await executor.run(
        WorkflowContext(
            input={
                "session": session,
                "send": send,
                "current_ig_cell": cell,
                "question": cell.input.rstrip(),
            }
        )
    )


async def update_planning_optimial_solution(cell: Cell, send, session: Session):
    opsmate_workflow_step = session.exec(
        select(OpsmateWorkflowStep)
        .where(OpsmateWorkflowStep.id == cell.internal_workflow_step_id)
        .where(OpsmateWorkflowStep.workflow_id == cell.internal_workflow_id)
    ).first()
    if not opsmate_workflow_step:
        logger.error("Opsmate workflow step not found", cell_id=cell.id)
        return

    opsmate_workflow = opsmate_workflow_step.workflow

    executor = WorkflowExecutor(opsmate_workflow, session)
    await executor.mark_rerun(opsmate_workflow_step)

    await executor.run(
        WorkflowContext(
            input={
                "session": session,
                "send": send,
                "current_pos_cell": cell,
                "question_cell": cell.parent_cells(session)[0],
            }
        )
    )


async def update_planning_knowledge_retrieval(
    cell: Cell, swap: str, send, session: Session
):
    opsmate_workflow_step = session.exec(
        select(OpsmateWorkflowStep)
        .where(OpsmateWorkflowStep.id == cell.internal_workflow_step_id)
        .where(OpsmateWorkflowStep.workflow_id == cell.internal_workflow_id)
    ).first()
    if not opsmate_workflow_step:
        logger.error("Opsmate workflow step not found", cell_id=cell.id)
        return

    opsmate_workflow = opsmate_workflow_step.workflow

    executor = WorkflowExecutor(opsmate_workflow, session)
    await executor.mark_rerun(opsmate_workflow_step)

    await executor.run(
        WorkflowContext(
            input={
                "session": session,
                "send": send,
                "current_pkr_cell": cell,
            }
        )
    )


async def update_planning_task_plan(cell: Cell, swap: str, send, session: Session):
    pass


async def execute_polya_planning_instruction(
    cell: Cell, swap: str, send, session: Session
):
    msg = cell.input.rstrip()
    logger.info("executing polya understanding instruction", cell_id=cell.id, input=msg)

    await render_notes_output(cell, session, send, cell_state=CellStateEnum.RUNNING)

    blueprint = cell.workflow.blueprint
    understanding_workflow: Workflow = blueprint.find_workflow_by_name(
        session, WorkflowEnum.UNDERSTANDING
    )
    report_extracted_json = understanding_workflow.result
    report_extracted = ReportExtracted.model_validate_json(report_extracted_json)
    blueprint = (
        manage_planning_optimial_solution_cell
        >> manage_planning_knowledge_retrieval_cell
        >> manage_planning_task_plan_cell
        >> store_facts_and_plans
    )

    opsmate_workflow = build_workflow(
        "planning",
        "Plan the solution",
        blueprint,
        session,
    )
    executor = WorkflowExecutor(opsmate_workflow, session)
    ctx = WorkflowContext(
        input={
            "session": session,
            "send": send,
            "question_cell": cell,
            "report_extracted": report_extracted,
        }
    )
    await executor.run(ctx)

    await render_notes_output(cell, session, send, cell_state=CellStateEnum.COMPLETED)


async def execute_polya_execution_instruction(
    cell: Cell, swap: str, send, session: Session
):
    logger.info(
        "executing polya execution instruction", cell_id=cell.id, input=cell.input
    )

    await render_notes_output(cell, session, send, cell_state=CellStateEnum.RUNNING)

    blueprint = cell.workflow.blueprint
    planning_workflow: Workflow = blueprint.find_workflow_by_name(
        session, WorkflowEnum.PLANNING
    )
    workflow_result = json.loads(planning_workflow.result)
    task_plan = TaskPlan.model_validate(workflow_result["task_plan"])
    facts = Facts.model_validate(workflow_result["facts"])

    # switch to the working directory
    logger.info("switching to working directory")
    chdir_call = SysChdir(
        path=os.path.join(os.getenv("HOME"), ".opsmate", "github_repo")
    )
    await chdir_call()

    instruction = f"""
Given the facts:

<facts>
{yaml.dump(facts.model_dump())}
</facts>

And the goal:
<goal>
{task_plan.goal}
</goal>

Here are the tasks to be performed **ONLY**:

<tasks>
{"\n".join(f"* {task.task}" for task in task_plan.subtasks)}
</tasks>

<important>
* PR **must be raised** if you are asked to do so
* Verify the tasks are correct if you are working on a pre-existing branch
</important>
    """

    await react_streaming(cell, swap, send, session, iac_sme(instruction))


async def execute_notes_instruction(cell: Cell, swap: str, send, session: Session):
    logger.info("executing notes instruction", cell_id=cell.id)

    await render_notes_output(cell, session, send, cell_state=CellStateEnum.COMPLETED)


async def execute_bash_instruction(cell: Cell, swap: str, send, session: Session):
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

    outputs.append(
        {
            "type": "BashOutput",
            "output": combined_output,
        }
    )

    cell.output = pickle.dumps(outputs)
    cell.state = CellStateEnum.COMPLETED
    session.add(cell)
    session.commit()
    await send(
        Div(
            *[CellOutputRenderer(output).render() for output in outputs],
            hx_swap_oob=swap,
            id=f"cell-output-{cell.id}",
        )
    )


def home_body(db_session: Session, session_name: str, blueprint: BluePrint):
    active_workflow = blueprint.active_workflow(db_session)
    workflows = blueprint.workflows
    cells = active_workflow.cells

    logger.info(
        "home body",
        cells=[cell.id for cell in cells],
        sequence=[cell.sequence for cell in cells],
    )
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
                    cls="text-sm text-gray-700 marked prose max-w-none",
                ),
                cls="flex items-center gap-2",
            ),
            cls="bg-blue-50 p-4 rounded-lg border border-blue-100",
        ),
        hx_swap_oob="true",
        id="workflow-panel",
    )


def render_cell_container(cells: list[Cell], hx_swap_oob: str = None):
    div = Div(
        *[CellComponent(cell) for cell in cells],
        cls="space-y-4 mt-4",
        id="cells-container",
        ws_connect="/cell/run/ws/",
        hx_ext="ws",
    )
    if hx_swap_oob:
        div.hx_swap_oob = hx_swap_oob
    return div
