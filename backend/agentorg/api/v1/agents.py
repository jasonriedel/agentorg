from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.agent import Agent, SoulVersion
from ...schemas.agent import AgentResponse, SoulVersionResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=list[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.slug))
    return result.scalars().all()


@router.get("/{slug}", response_model=AgentResponse)
async def get_agent(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.slug == slug))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, f"Agent '{slug}' not found")
    return agent


@router.get("/{slug}/soul", response_model=SoulVersionResponse)
async def get_active_soul(slug: str, db: AsyncSession = Depends(get_db)):
    agent = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
    if not agent:
        raise HTTPException(404, f"Agent '{slug}' not found")
    soul = (await db.execute(
        select(SoulVersion)
        .where(SoulVersion.agent_id == agent.id, SoulVersion.is_active.is_(True))
        .order_by(SoulVersion.created_at.desc())
    )).scalar_one_or_none()
    if not soul:
        raise HTTPException(404, f"No active soul version for '{slug}'")
    return soul


@router.get("/{slug}/soul/versions", response_model=list[SoulVersionResponse])
async def list_soul_versions(slug: str, db: AsyncSession = Depends(get_db)):
    agent = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
    if not agent:
        raise HTTPException(404, f"Agent '{slug}' not found")
    versions = (await db.execute(
        select(SoulVersion)
        .where(SoulVersion.agent_id == agent.id)
        .order_by(SoulVersion.created_at.desc())
    )).scalars().all()
    return versions
