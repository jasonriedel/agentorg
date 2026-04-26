from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .config import settings
from .database import AsyncSessionLocal, Base, engine
from .models import Agent, Artifact, Gate, Run, RunEvent, RunStatus, SoulVersion, Task, TaskStatus, Workflow
from .core.soul_manager import SoulManager
from .core.workflow_parser import parse_workflow
from .api.v1 import workflows as workflows_router
from .api.v1 import runs as runs_router
from .api.v1 import gates as gates_router
from .api.v1 import agents as agents_router
from .api.v1 import webhooks as webhooks_router
from .api.ws import events as ws_events_router
from .services.soul_sync_service import get_soul_sync_service
from .services.trigger_service import get_trigger_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _seed_workflows()
    await _seed_agents()

    sync_service = get_soul_sync_service()
    await sync_service.start()

    trigger_svc = get_trigger_service()
    trigger_svc.start()
    await trigger_svc.load_cron_schedules()

    yield

    await sync_service.stop()
    trigger_svc.stop()


async def _seed_workflows() -> None:
    workflows_path = Path(settings.workflows_dir)
    if not workflows_path.exists():
        return

    async with AsyncSessionLocal() as db:
        for yaml_file in sorted(workflows_path.glob("*.yaml")):
            try:
                wf_def = parse_workflow(yaml_file)
                existing = (await db.execute(select(Workflow).where(Workflow.slug == wf_def.slug))).scalar_one_or_none()
                if not existing:
                    definition = {"phases": wf_def.phases, "tasks": [asdict(t) for t in wf_def.tasks]}
                    db.add(Workflow(
                        slug=wf_def.slug,
                        name=wf_def.name,
                        description=wf_def.description,
                        definition_yaml=wf_def.raw_yaml,
                        definition=definition,
                    ))
                    print(f"[seed] workflow: {wf_def.name}")
            except Exception as e:
                print(f"[seed] skipped {yaml_file.name}: {e}")
        await db.commit()


async def _seed_agents() -> None:
    """Register agents from souls directory, seeding DB records and initial SoulVersions."""
    soul_manager = SoulManager(settings.souls_dir)
    slugs = soul_manager.list_slugs()

    async with AsyncSessionLocal() as db:
        for slug in sorted(slugs):
            try:
                soul = soul_manager.load(slug)
                existing = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
                if not existing:
                    agent = Agent(slug=slug, name=soul.name, current_soul_version=soul.version)
                    db.add(agent)
                    await db.flush()

                    sv = SoulVersion(
                        agent_id=agent.id,
                        version=soul.version,
                        soul_md=soul.raw_md,
                        is_active=True,
                    )
                    db.add(sv)
                    print(f"[seed] agent: {slug} v{soul.version}")
            except Exception as e:
                print(f"[seed] agent skipped {slug}: {e}")
        await db.commit()


app = FastAPI(title="AgentOrg", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflows_router.router, prefix="/api/v1")
app.include_router(runs_router.router, prefix="/api/v1")
app.include_router(gates_router.router, prefix="/api/v1")
app.include_router(agents_router.router, prefix="/api/v1")
app.include_router(webhooks_router.router)  # no prefix — /webhooks/github
app.include_router(ws_events_router.router)  # WebSocket — no prefix


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.3.0"}
