from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...core.agent_runner import AgentRunner
from ...core.orchestrator import Orchestrator
from ...core.soul_manager import SoulManager
from ...core.workflow_parser import parse_workflow, WorkflowDef
from ...database import AsyncSessionLocal, get_db
from ...models.run import Run
from ...models.workflow import Workflow
from ...schemas.run import RunResponse
from ...schemas.workflow import TriggerWorkflowRequest, WorkflowResponse
from ...tools.context_tools import GET_CONTEXT, SET_CONTEXT
from ...tools.file_tools import LIST_FILES, READ_FILE, WRITE_FILE
from ...tools.github_tools import COMMIT_FILES, CREATE_BRANCH, CREATE_PR
from ...tools.registry import ToolRegistry

router = APIRouter(prefix="/workflows", tags=["workflows"])


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in [READ_FILE, WRITE_FILE, LIST_FILES, CREATE_BRANCH, COMMIT_FILES, CREATE_PR, GET_CONTEXT, SET_CONTEXT]:
        registry.register(tool)
    return registry


@router.get("/", response_model=list[WorkflowResponse])
async def list_workflows(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workflow).where(Workflow.is_active.is_(True)))
    return result.scalars().all()


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Workflow).where((Workflow.slug == workflow_id) | (Workflow.id == workflow_id))
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(404, f"Workflow '{workflow_id}' not found")
    return wf


@router.post("/{workflow_id}/trigger", response_model=RunResponse, status_code=202)
async def trigger_workflow(
    workflow_id: str,
    request: TriggerWorkflowRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Workflow).where(
            ((Workflow.slug == workflow_id) | (Workflow.id == workflow_id)) & Workflow.is_active.is_(True)
        )
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(404, f"Workflow '{workflow_id}' not found")

    workflow_path = Path(settings.workflows_dir) / f"{wf.slug}.yaml"
    if not workflow_path.exists():
        raise HTTPException(500, f"Workflow definition file not found: {workflow_path}")

    workflow_def = parse_workflow(workflow_path)

    run = Run(
        workflow_id=wf.id,
        workflow_slug=wf.slug,
        trigger="manual",
        trigger_payload={"inputs": request.inputs},
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    background_tasks.add_task(_execute_run, run.id, workflow_def)

    return run


async def _execute_run(run_id: str, workflow_def: WorkflowDef) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one()

        soul_manager = SoulManager(settings.souls_dir)
        agent_runner = AgentRunner(build_registry())
        orchestrator = Orchestrator(soul_manager, agent_runner)

        await orchestrator.execute_run(run, workflow_def, db)
