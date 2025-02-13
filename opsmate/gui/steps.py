from opsmate.gui.models import (
    Cell,
    CellLangEnum,
    ThinkingSystemEnum,
    CellType,
    CreatedByType,
)

from opsmate.polya.models import (
    InitialUnderstandingResponse,
    NonTechnicalQuery,
    InfoGathered,
    ReportExtracted,
    Solution,
)

from opsmate.polya.understanding import (
    initial_understanding,
    load_inital_understanding,
    info_gathering,
    generate_report,
    report_breakdown,
)

from opsmate.polya.planning import (
    planning,
    summary_breakdown,
    knowledge_retrieval,
    load_facts,
)
from opsmate.polya.models import (
    TaskPlan,
    Facts,
)
from opsmate.polya.execution import (
    execution,
)
from opsmate.workflow.workflow import (
    WorkflowContext,
    Workflow,
    step,
    step_factory,
)
from opsmate.gui.components import CellComponent, CellOutputRenderer
from opsmate.gui.views import conversation_context
import structlog
import pickle
import json
from sqlmodel import Session
from fasthtml.common import *

logger = structlog.get_logger()


async def initial_understanding_success_hook(ctx: WorkflowContext, result):
    session = ctx.input["session"]
    cell, _ = result
    cell = Cell.find_by_id(session, cell.id)

    cell.internal_workflow_id = ctx.workflow_id
    cell.internal_workflow_step_id = ctx.step_id

    session.add(cell)
    session.commit()


@step(post_success_hooks=[initial_understanding_success_hook])
async def manage_initial_understanding_cell(
    ctx: WorkflowContext,
):
    parent_cell = ctx.input["question_cell"]
    session = ctx.input["session"]
    send = ctx.input["send"]
    workflow = Workflow.find_by_id(session, parent_cell.workflow_id)
    cells = workflow.cells
    # get the highest sequence number
    max_sequence = max(cell.sequence for cell in cells) if cells else 0
    # get the higest execution sequence number
    max_execution_sequence = (
        max(cell.execution_sequence for cell in cells) if cells else 0
    )
    context = [
        conversation for conversation in conversation_context(parent_cell, session)
    ]
    cell = ctx.input.get("current_iu_cell")
    is_new_cell = cell is None
    if is_new_cell:
        iu = await initial_understanding(
            parent_cell.input.rstrip(), chat_history=context
        )
    else:
        iu = await load_inital_understanding(cell.input)
        iu = InitialUnderstandingResponse(**iu.model_dump())

    if is_new_cell:
        logger.info("creating new initial understanding cell")
        cell = Cell(
            input="",
            output=b"",
            lang=CellLangEnum.TEXT_INSTRUCTION,
            thinking_system=ThinkingSystemEnum.TYPE2,
            sequence=max_sequence + 1,
            execution_sequence=max_execution_sequence + 1,
            active=True,
            workflow_id=parent_cell.workflow_id,
            cell_type=CellType.UNDERSTANDING_ASK_QUESTIONS,
            created_by=CreatedByType.ASSISTANT,
            parent_cell_ids=[parent_cell.id],
            hidden=True,
        )
        session.add(cell)
        session.commit()

        workflow.activate_cell(session, cell.id)
        session.commit()
    else:
        logger.info("updating existing initial understanding cell", cell_id=cell.id)
        cell.hidden = True
        cell.execution_sequence = max_execution_sequence + 1
        cell.output = pickle.dumps(
            [
                {
                    "type": "InitialUnderstanding",
                    "output": iu,
                }
            ]
        )
        session.add(cell)
        session.commit()
        await send(CellComponent(cell, hx_swap_oob="true"))
        return cell, iu
    outputs = []
    await send(
        Div(
            *outputs,
            hx_swap_oob="true",
            id=f"cell-output-{cell.id}",
        )
    )
    if isinstance(iu, NonTechnicalQuery):
        outputs.append(
            {
                "type": "NonTechnicalQuery",
                "output": NonTechnicalQuery(**iu.model_dump()),
            }
        )

        cell.output = pickle.dumps(outputs)
        session.add(cell)
        session.commit()

        # can only be a new cell
        await send(
            Div(
                CellComponent(cell),
                hx_swap_oob="beforeend",
                id="cells-container",
            )
        )

        return cell, None

    outputs.append(
        {
            "type": "InitialUnderstanding",
            "output": InitialUnderstandingResponse(**iu.model_dump()),
        }
    )

    logger.info("initial understanding output", outputs=outputs)

    cell.output = pickle.dumps(outputs)

    cell.input = CellOutputRenderer(outputs[0]).render()[0]
    session.add(cell)
    session.commit()

    await send(
        Div(
            CellComponent(cell),
            hx_swap_oob="beforeend",
            id="cells-container",
        )
    )

    return cell, iu


@step
async def cond_is_technical_query(ctx: WorkflowContext):
    _, iu = ctx.step_results
    return iu is not None


@step
async def generate_report_with_breakdown(ctx: WorkflowContext):
    session = ctx.input["session"]
    send = ctx.input["send"]
    cells, info_gathered = zip(*ctx.step_results)
    cells, info_gathered = (
        list([cell for cell in cells if cell is not None]),
        list([info for info in info_gathered if info is not None]),
    )
    initial_understanding_result = ctx.find_result(
        "manage_initial_understanding_cell", session
    )
    _, iu = initial_understanding_result
    summary = iu.summary

    report = await generate_report(summary, info_gathered=info_gathered)
    report_extracted = await report_breakdown(report)

    return cells, ReportExtracted(**report_extracted.model_dump())


def make_manage_potential_solution_cell(solution_id: int):
    async def success_hook(ctx: WorkflowContext, result):
        if result is None:
            return
        session = ctx.input["session"]
        cell = Cell.find_by_id(session, result.id)
        cell.internal_workflow_id = ctx.workflow_id
        cell.internal_workflow_step_id = ctx.step_id
        session.add(cell)
        session.commit()

    @step_factory
    @step(post_success_hooks=[success_hook])
    async def manage_potential_solution_cell(ctx: WorkflowContext):
        cells, report_extracted = ctx.step_results
        session = ctx.input["session"]
        send = ctx.input["send"]
        solution_id = ctx.metadata["solution_id"]
        if len(report_extracted.potential_solutions) <= solution_id:
            return None
        return await __manage_potential_solution_cell(
            cells,
            report_extracted.summary,
            report_extracted.potential_solutions[solution_id],
            session,
            send,
        )

    return manage_potential_solution_cell(metadata={"solution_id": solution_id})


manage_potential_solution_cells = [
    make_manage_potential_solution_cell(0),
    make_manage_potential_solution_cell(1),
    make_manage_potential_solution_cell(2),
]


@step
async def store_report_extracted(ctx: WorkflowContext):
    session = ctx.input["session"]

    cells, report_extracted = ctx.find_result("generate_report_with_breakdown", session)

    workflow = Workflow.find_by_id(session, cells[0].workflow_id)
    workflow.result = report_extracted.model_dump_json()
    session.add(workflow)
    session.commit()


def make_manage_info_gathering_cell(question_id: int):
    async def success_hook(ctx: WorkflowContext, result):
        session = ctx.input["session"]
        cell, _ = result
        if cell is None:
            return
        cell = Cell.find_by_id(session, cell.id)
        cell.internal_workflow_id = ctx.workflow_id
        cell.internal_workflow_step_id = ctx.step_id
        session.add(cell)
        session.commit()

    @step_factory
    @step(
        post_success_hooks=[success_hook],
    )
    async def manage_info_gathering_cell(
        ctx: WorkflowContext,
    ):
        session = ctx.input["session"]
        send = ctx.input["send"]
        parent_cell, iu = ctx.find_result("manage_initial_understanding_cell", session)
        workflow = Workflow.find_by_id(session, parent_cell.workflow_id)

        cell = ctx.input.get("current_ig_cell")
        is_new_cell = cell is None

        if not is_new_cell:
            await send(
                Div(
                    hx_swap_oob="true",
                    id=f"cell-output-{cell.id}",
                )
            )

        if ctx.input.get("question"):
            question = ctx.input.get("question")
        else:
            if len(iu.questions) <= ctx.metadata["question_id"]:
                return None, None
            question = iu.questions[ctx.metadata["question_id"]]
        logger.info("info gathering", question=question)
        info_gathered = await info_gathering(iu.summary, question)
        info_gathered = InfoGathered(**info_gathered.model_dump())

        outputs = []
        outputs.append(
            {
                "type": "InfoGathered",
                "output": info_gathered,
            }
        )

        cells = workflow.cells
        # get the highest sequence number
        max_sequence = max(c.sequence for c in cells) if cells else 0
        # get the higest execution sequence number
        max_execution_sequence = (
            max(c.execution_sequence for c in cells) if cells else 0
        )
        if is_new_cell:
            logger.info("creating new info gathering cell")
            cell = Cell(
                input=info_gathered.question,
                output=pickle.dumps(outputs),
                lang=CellLangEnum.TEXT_INSTRUCTION,
                thinking_system=ThinkingSystemEnum.TYPE2,
                sequence=max_sequence + 1,
                execution_sequence=max_execution_sequence + 1,
                active=True,
                workflow_id=parent_cell.workflow_id,
                parent_cell_ids=[parent_cell.id],
                cell_type=CellType.UNDERSTANDING_GATHER_INFO,
                created_by=CreatedByType.ASSISTANT,
                hidden=True,
            )
        else:
            logger.info("updating existing info gathering cell", cell_id=cell.id)
            info_gathered = InfoGathered(**info_gathered.model_dump())
            cell.output = pickle.dumps(outputs)
            cell.hidden = True

        session.add(cell)
        session.commit()

        workflow.activate_cell(session, cell.id)
        session.commit()

        if is_new_cell:
            await send(
                Div(
                    CellComponent(cell),
                    hx_swap_oob="beforeend",
                    id="cells-container",
                )
            )
        else:
            await send(CellComponent(cell, hx_swap_oob="true"))

        return cell, info_gathered

    return manage_info_gathering_cell(metadata={"question_id": question_id})


manage_info_gather_cells = [
    make_manage_info_gathering_cell(0),
    make_manage_info_gathering_cell(1),
    make_manage_info_gathering_cell(2),
]


async def __manage_potential_solution_cell(
    parent_cells: list[Cell],
    summary: str,
    solution: Solution,
    session: Session,
    send,
):
    workflow = Workflow.find_by_id(session, parent_cells[0].workflow_id)
    cells = workflow.cells
    # get the highest sequence number
    max_sequence = max(cell.sequence for cell in cells) if cells else 0
    # get the higest execution sequence number
    max_execution_sequence = (
        max(cell.execution_sequence for cell in cells) if cells else 0
    )

    outputs = []
    output = {
        "summary": summary,
        "solution": Solution(**solution.model_dump()),
    }
    outputs.append(
        {
            "type": "PotentialSolution",
            "output": output,
        }
    )

    cell = Cell(
        input=CellOutputRenderer(outputs[0]).render()[0],
        output=pickle.dumps(outputs),
        lang=CellLangEnum.NOTES,
        thinking_system=ThinkingSystemEnum.TYPE1,
        sequence=max_sequence + 1,
        execution_sequence=max_execution_sequence + 1,
        active=True,
        workflow_id=parent_cells[0].workflow_id,
        parent_cell_ids=[parent_cell.id for parent_cell in parent_cells],
        cell_type=CellType.UNDERSTANDING_SOLUTION,
        created_by=CreatedByType.ASSISTANT,
        hidden=True,
    )
    session.add(cell)
    session.commit()

    workflow.activate_cell(session, cell.id)
    session.commit()

    await send(
        Div(
            CellComponent(cell),
            hx_swap_oob="beforeend",
            id="cells-container",
        )
    )

    return cell


@step
async def empty_cell(ctx: WorkflowContext):
    session = ctx.input["session"]
    cell = ctx.input["question_cell"]
    send = ctx.input["send"]
    await send(
        Div(
            hx_swap_oob="true",
            id=f"cell-output-{cell.id}",
        )
    )


async def success_hook(ctx: WorkflowContext, result):
    session = ctx.input["session"]
    if result is None:
        return
    cell, _ = result
    if cell is None:
        return
    cell = Cell.find_by_id(session, cell.id)
    cell.internal_workflow_id = ctx.workflow_id
    cell.internal_workflow_step_id = ctx.step_id
    session.add(cell)
    session.commit()


@step(post_success_hooks=[success_hook])
async def manage_planning_optimial_solution_cell(ctx: WorkflowContext):
    parent_cell = ctx.input["question_cell"]
    session = ctx.input["session"]
    send = ctx.input["send"]
    report_extracted: ReportExtracted | None = ctx.input.get("report_extracted")
    workflow = Workflow.find_by_id(session, parent_cell.workflow_id)
    cells = workflow.cells
    # get the highest sequence number
    max_sequence = max(cell.sequence for cell in cells) if cells else 0
    # get the higest execution sequence number
    max_execution_sequence = (
        max(cell.execution_sequence for cell in cells) if cells else 0
    )

    context = [
        conversation for conversation in conversation_context(parent_cell, session)
    ]
    cell = ctx.input.get("current_pos_cell")
    is_new_cell = cell is None
    if is_new_cell:
        # xxx: fill the extra context
        solution = report_extracted.potential_solutions[0]
        summary = report_extracted.summary
        solution_for_planning = solution.summarize(summary)
    else:
        solution_for_planning = cell.input.rstrip()
    outputs = []
    output = solution_for_planning
    outputs.append(
        {
            "type": "SolutionForPlanning",
            "output": output,
        }
    )

    if is_new_cell:
        logger.info("creating new planning optimial solution cell")
        cell = Cell(
            input=CellOutputRenderer(outputs[0]).render()[0],
            output=pickle.dumps(outputs),
            lang=CellLangEnum.TEXT_INSTRUCTION,
            thinking_system=ThinkingSystemEnum.TYPE2,
            sequence=max_sequence + 1,
            execution_sequence=max_execution_sequence + 1,
            active=True,
            workflow_id=parent_cell.workflow_id,
            parent_cell_ids=[parent_cell.id],
            cell_type=CellType.PLANNING_OPTIMAL_SOLUTION,
            created_by=CreatedByType.ASSISTANT,
            hidden=True,
        )
        session.add(cell)
        session.commit()

        workflow.activate_cell(session, cell.id)
        session.commit()

        await send(
            Div(
                CellComponent(cell),
                hx_swap_oob="beforeend",
                id="cells-container",
            )
        )
    else:
        logger.info(
            "updating existing planning optimial solution cell", cell_id=cell.id
        )
        cell.hidden = True
        cell.execution_sequence = max_execution_sequence + 1
        cell.output = pickle.dumps(outputs)
        session.add(cell)
        session.commit()

        await send(CellComponent(cell, hx_swap_oob="true"))
    return cell, solution_for_planning


@step(post_success_hooks=[success_hook])
async def manage_planning_knowledge_retrieval_cell(ctx: WorkflowContext):
    session = ctx.input["session"]
    send = ctx.input["send"]
    parent_cell, summary = ctx.find_result(
        "manage_planning_optimial_solution_cell", session
    )
    workflow = Workflow.find_by_id(session, parent_cell.workflow_id)

    cell = ctx.input.get("current_pkr_cell")
    if cell:
        cell = Cell.find_by_id(session, cell.id)
    is_new_cell = cell is None

    if is_new_cell:
        questions = await summary_breakdown(summary)
        logger.info("questions", questions=questions)
        facts = await knowledge_retrieval(questions)

    else:
        logger.info("loading facts from existing cell", cell_id=cell.id)
        facts = await load_facts(cell.input.rstrip())
    facts = Facts(**facts.model_dump())
    logger.info("facts", facts=facts)

    cells = workflow.cells
    # get the highest sequence number
    max_sequence = max(cell.sequence for cell in cells) if cells else 0
    # get the higest execution sequence number
    max_execution_sequence = (
        max(cell.execution_sequence for cell in cells) if cells else 0
    )

    outputs = []
    output = {
        "type": "Facts",
        "output": facts,
    }
    outputs.append(output)
    if is_new_cell:
        logger.info("creating new planning knowledge retrieval cell")
        cell = Cell(
            input=CellOutputRenderer(outputs[0]).render()[0],
            output=pickle.dumps(outputs),
            lang=CellLangEnum.TEXT_INSTRUCTION,
            thinking_system=ThinkingSystemEnum.TYPE2,
            sequence=max_sequence + 1,
            execution_sequence=max_execution_sequence + 1,
            active=True,
            workflow_id=parent_cell.workflow_id,
            parent_cell_ids=[parent_cell.id],
            cell_type=CellType.PLANNING_KNOWLEDGE_RETRIEVAL,
            created_by=CreatedByType.ASSISTANT,
            hidden=True,
        )

    else:
        logger.info(
            "updating existing planning knowledge retrieval cell", cell_id=cell.id
        )
        cell.hidden = True
        cell.execution_sequence = max_execution_sequence + 1
        cell.output = pickle.dumps(outputs)

    session.add(cell)
    session.commit()

    workflow.activate_cell(session, cell.id)
    session.commit()

    if is_new_cell:
        await send(
            Div(
                CellComponent(cell),
                hx_swap_oob="beforeend",
                id="cells-container",
            )
        )
    else:
        await send(CellComponent(cell, hx_swap_oob="true"))

    return cell, facts


@step(post_success_hooks=[success_hook])
async def manage_planning_task_plan_cell(ctx: WorkflowContext):
    session = ctx.input["session"]
    send = ctx.input["send"]
    parent_cell, facts = ctx.find_result(
        "manage_planning_knowledge_retrieval_cell", session
    )
    _, solution_for_planning = ctx.find_result(
        "manage_planning_optimial_solution_cell", session
    )
    workflow = Workflow.find_by_id(session, parent_cell.workflow_id)
    cells = workflow.cells
    # get the highest sequence number
    max_sequence = max(cell.sequence for cell in cells) if cells else 0
    # get the higest execution sequence number
    max_execution_sequence = (
        max(cell.execution_sequence for cell in cells) if cells else 0
    )

    task_plan = await planning(
        summary=solution_for_planning,
        facts=facts.facts,
        instruction="how to solve the problem?",
    )
    task_plan = TaskPlan(**task_plan.model_dump())
    outputs = []
    output = {
        "type": "TaskPlan",
        "output": task_plan,
    }
    outputs.append(output)

    # xxx: always create a new cell for now
    cell = Cell(
        input=CellOutputRenderer(outputs[0]).render()[0],
        output=pickle.dumps(outputs),
        lang=CellLangEnum.TEXT_INSTRUCTION,
        thinking_system=ThinkingSystemEnum.TYPE2,
        sequence=max_sequence + 1,
        execution_sequence=max_execution_sequence + 1,
        active=True,
        workflow_id=parent_cell.workflow_id,
        parent_cell_ids=[parent_cell.id],
        cell_type=CellType.PLANNING_TASK_PLAN,
        created_by=CreatedByType.ASSISTANT,
        hidden=True,
    )

    session.add(cell)
    session.commit()

    workflow.activate_cell(session, cell.id)
    session.commit()

    await send(
        Div(
            CellComponent(cell),
            hx_swap_oob="beforeend",
            id="cells-container",
        )
    )

    return cell, task_plan


@step
async def store_facts_and_plans(ctx: WorkflowContext):
    session = ctx.input["session"]

    _, task_plan = ctx.find_result("manage_planning_task_plan_cell", session)
    cell, facts = ctx.find_result("manage_planning_knowledge_retrieval_cell", session)
    workflow = Workflow.find_by_id(session, cell.workflow_id)
    workflow.result = json.dumps(
        {
            "task_plan": task_plan.model_dump(),
            "facts": facts.model_dump(),
        }
    )
    session.add(workflow)
    session.commit()
