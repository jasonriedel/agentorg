from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.run import Run, Task
from ...schemas.run import RunResponse, TaskResponse

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/", response_model=list[RunResponse])
async def list_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Run).order_by(Run.created_at.desc()).limit(50))
    return result.scalars().all()


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.get("/{run_id}/tasks", response_model=list[TaskResponse])
async def get_run_tasks(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.run_id == run_id).order_by(Task.created_at))
    return result.scalars().all()
