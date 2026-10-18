
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ActionRequest(BaseModel):
    action_id: str
    agent_id: str
    session_id: str
    task_id: str
    operation: Literal["SELECT", "INSERT", "UPDATE", "DELETE"]
    resource: str

    @field_validator("operation", mode="before")
    @classmethod
    def normalize_operation(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().upper()
        return v


class DecisionResponse(BaseModel):
    action_id: str
    decision: Literal["ALLOW", "HOLD", "BLOCK"]
    reason: str
    risk_score: int = Field(ge=0, le=100)
    executed: bool


# Compatibility aliases for API contract naming
EvaluateRequest = ActionRequest
EvaluateResponse = DecisionResponse

__all__ = [
    "ActionRequest",
    "DecisionResponse",
    "EvaluateRequest",
    "EvaluateResponse",
]
