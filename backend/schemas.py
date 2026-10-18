from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


class ActionRequest(BaseModel):
    action_id: str
    agent_id: str
    session_id: str
    task_id: str
    operation: str
    resource: str

    @field_validator("operation", mode="before")
    @classmethod
    def normalize_operation(cls, v: Any) -> str:
        if isinstance(v, str):
            cleaned = v.strip().upper()
            # Map operational synonyms to standard database verbs
            if cleaned == "READ":
                return "SELECT"
            if cleaned == "WRITE":
                return "UPDATE"
            return cleaned
        return str(v).strip().upper()


class DecisionResponse(BaseModel):
    action_id: str
    decision: Literal["ALLOW", "HOLD", "BLOCK"]
    reason: str
    risk_score: int = Field(ge=0, le=100)
    executed: bool


class TaskRegistrationRequest(BaseModel):
    task_id: str
    agent_id: str = "agent_01"
    purpose: str = "Declared agent task purpose"
    allowed_operations: list[str] = Field(default_factory=lambda: ["SELECT"])
    allowed_resources: list[str] = Field(default_factory=lambda: ["transactions"])
    requires_review_for: list[str] = Field(default_factory=list)

    @field_validator("allowed_operations", "requires_review_for", mode="before")
    @classmethod
    def normalize_operations_list(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            res = []
            for item in v:
                cleaned = str(item).strip().upper()
                if cleaned == "READ":
                    cleaned = "SELECT"
                elif cleaned == "WRITE":
                    cleaned = "UPDATE"
                res.append(cleaned)
            return res
        return []

    @field_validator("allowed_resources", mode="before")
    @classmethod
    def normalize_resources_list(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(item).strip().lower() for item in v]
        return []


class TaskRegistrationResponse(BaseModel):
    task_id: str
    status: str = "registered"
    message: str = "Task policy registered successfully"
    policy: dict[str, Any] = Field(default_factory=dict)


# Compatibility aliases for API contract naming
EvaluateRequest = ActionRequest
EvaluateResponse = DecisionResponse

__all__ = [
    "ActionRequest",
    "DecisionResponse",
    "EvaluateRequest",
    "EvaluateResponse",
    "TaskRegistrationRequest",
    "TaskRegistrationResponse",
]
