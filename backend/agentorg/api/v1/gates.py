from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.gate_manager import get_gate_manager
from ...database import get_db
from ...models.gate import Gate

router = APIRouter(prefix="/runs", tags=["gates"])


class GateResponseRequest(BaseModel):
    action: str  # "approved" or "rejected"
    feedback: str | None = None


@router.post("/{run_id}/gates/{gate_id}")
async def respond_to_gate(
    run_id: str,
    gate_id: str,
    request: GateResponseRequest,
    db: AsyncSession = Depends(get_db),
):
    if request.action not in ("approved", "rejected"):
        raise HTTPException(400, "action must be 'approved' or 'rejected'")

    result = await db.execute(
        select(Gate).where(Gate.id == gate_id, Gate.run_id == run_id)
    )
    gate = result.scalar_one_or_none()
    if not gate:
        raise HTTPException(404, "Gate not found")
    if gate.status != "waiting":
        raise HTTPException(409, f"Gate already resolved: {gate.status}")

    manager = get_gate_manager()
    resolved = manager.resolve(gate_id, action=request.action, feedback=request.feedback)
    if not resolved:
        raise HTTPException(409, "Gate not pending in manager — run may have restarted")

    return {"gate_id": gate_id, "action": request.action}


@router.get("/{run_id}/gates")
async def list_gates(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Gate).where(Gate.run_id == run_id).order_by(Gate.created_at))
    return [
        {
            "id": g.id,
            "name": g.name,
            "message": g.message,
            "status": g.status,
            "response": g.response,
            "created_at": g.created_at.isoformat(),
            "resolved_at": g.resolved_at.isoformat() if g.resolved_at else None,
        }
        for g in result.scalars()
    ]
