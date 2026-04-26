"""APScheduler-based cron trigger service for scheduled workflows."""
import asyncio
import logging
from dataclasses import asdict
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from ..config import settings
from ..core.workflow_parser import parse_workflow, WorkflowDef
from ..database import AsyncSessionLocal
from ..models.run import Run
from ..models.workflow import Workflow

logger = logging.getLogger(__name__)


class TriggerService:
    def __init__(self):
        self._scheduler = AsyncIOScheduler()
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._scheduler.start()
        self._started = True
        logger.info("[trigger_service] started")

    def stop(self) -> None:
        if self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False

    def schedule_cron(self, workflow_slug: str, cron_config: dict) -> None:
        """Schedule a cron trigger from YAML config like: {minute: '*/15'}."""
        job_id = f"cron:{workflow_slug}"
        if self._scheduler.get_job(job_id):
            return

        # APScheduler cron kwargs — subset of standard cron fields
        allowed = {"year", "month", "day", "week", "day_of_week", "hour", "minute", "second"}
        kwargs = {k: v for k, v in cron_config.items() if k in allowed}

        self._scheduler.add_job(
            self._fire_workflow,
            "cron",
            id=job_id,
            args=[workflow_slug],
            replace_existing=True,
            **kwargs,
        )
        logger.info(f"[trigger_service] scheduled cron for '{workflow_slug}': {kwargs}")

    async def _fire_workflow(self, workflow_slug: str, inputs: dict | None = None) -> None:
        """Create a Run and execute it in background."""
        from ..core.soul_manager import SoulManager
        from ..core.agent_runner import AgentRunner
        from ..core.orchestrator import Orchestrator
        from ..api.v1.workflows import build_registry

        workflow_path = Path(settings.workflows_dir) / f"{workflow_slug}.yaml"
        if not workflow_path.exists():
            logger.warning(f"[trigger_service] workflow file not found: {workflow_path}")
            return

        workflow_def = parse_workflow(workflow_path)

        async with AsyncSessionLocal() as db:
            wf_row = (await db.execute(
                select(Workflow).where(Workflow.slug == workflow_slug)
            )).scalar_one_or_none()
            if not wf_row:
                logger.warning(f"[trigger_service] workflow '{workflow_slug}' not in DB")
                return

            run = Run(
                workflow_id=wf_row.id,
                workflow_slug=workflow_slug,
                trigger="cron",
                trigger_payload={"inputs": inputs or {}},
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)

        logger.info(f"[trigger_service] firing '{workflow_slug}' run={run.id[:8]}")
        asyncio.create_task(_execute_run_bg(run.id, workflow_def))

    async def load_cron_schedules(self) -> None:
        """Read all active workflows and schedule any cron triggers."""
        workflows_path = Path(settings.workflows_dir)
        if not workflows_path.exists():
            return

        for yaml_file in workflows_path.glob("*.yaml"):
            try:
                wf_def = parse_workflow(yaml_file)
                for trigger in wf_def.triggers:
                    if trigger.get("type") == "cron":
                        self.schedule_cron(wf_def.slug, trigger.get("config", {}))
            except Exception as e:
                logger.warning(f"[trigger_service] skipped {yaml_file.name}: {e}")


async def _execute_run_bg(run_id: str, workflow_def: WorkflowDef) -> None:
    from ..core.soul_manager import SoulManager
    from ..core.agent_runner import AgentRunner
    from ..core.orchestrator import Orchestrator
    from ..api.v1.workflows import build_registry

    async with AsyncSessionLocal() as db:
        run = (await db.execute(select(Run).where(Run.id == run_id))).scalar_one()
        soul_manager = SoulManager(settings.souls_dir)
        agent_runner = AgentRunner(build_registry())
        orchestrator = Orchestrator(soul_manager, agent_runner)
        try:
            await orchestrator.execute_run(run, workflow_def, db)
        except Exception as e:
            logger.error(f"[trigger_service] run {run_id[:8]} failed: {e}")


_service: TriggerService | None = None


def get_trigger_service() -> TriggerService:
    global _service
    if _service is None:
        _service = TriggerService()
    return _service
