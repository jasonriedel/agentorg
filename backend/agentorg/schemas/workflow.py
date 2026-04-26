from typing import Any

from pydantic import BaseModel


class TriggerWorkflowRequest(BaseModel):
    inputs: dict[str, Any] = {}


class WorkflowResponse(BaseModel):
    id: str
    slug: str
    name: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}
