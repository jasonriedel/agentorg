from datetime import datetime

from pydantic import BaseModel


class RunResponse(BaseModel):
    id: str
    workflow_id: str
    workflow_slug: str
    status: str
    phase: str | None
    cost_usd: float
    token_count: int
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: str
    agent_slug: str
    name: str
    phase: str
    status: str
    output_summary: str | None
    full_output: str | None
    token_count: int
    cost_usd: float
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None

    model_config = {"from_attributes": True}
