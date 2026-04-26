from datetime import datetime

from pydantic import BaseModel


class SoulVersionResponse(BaseModel):
    id: str
    version: str
    soul_md: str
    commit_sha: str | None
    pr_url: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentResponse(BaseModel):
    id: str
    slug: str
    name: str
    current_soul_version: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
