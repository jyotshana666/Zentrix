
from typing import Literal

from pydantic import BaseModel, Field


class ActionRequest(BaseModel):
    action_id: str
    agent_id: str
    session_id: str
    task_id: str
    operation: Literal["SELECT", "INSERT", "UPDATE", "DELETE"]
    resource: str


class DecisionResponse(BaseModel):
    action_id: str
    decision: Literal["ALLOW", "HOLD", "BLOCK"]
    reason: str
    risk_score: int = Field(ge=0, le=100)
    executed: bool
