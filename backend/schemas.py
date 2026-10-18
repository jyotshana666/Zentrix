from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action_id: str
    agent_id: str
    session_id: str
    task_id: str
    operation: str
    resource: str
    timestamp: str | None = None

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
    model_config = ConfigDict(extra="allow")

    action_id: str
    decision: Literal["ALLOW", "HOLD", "BLOCK"]
    reason: str
    risk_score: int = Field(ge=0, le=100)
    executed: bool


class TaskRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

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


class ReviewActionRequest(BaseModel):
    decision: Literal["APPROVE", "REJECT", "APPROVED", "REJECTED"] = "APPROVE"
    reviewer_id: str = "sec_analyst_01"
    notes: str = "Manual security authorization"


class ReviewActionResponse(BaseModel):
    action_id: str
    status: str
    decision: str
    executed: bool
    message: str


class MetricsResponse(BaseModel):
    prevention_rate: float
    false_hold_rate: float
    drift_detection_recall: float
    drift_precision: float
    average_latency_ms: float
    total_actions_evaluated: int
    total_allowed: int
    total_held: int
    total_blocked: int
    unauthorized_executions_count: int


class AgentRiskResponse(BaseModel):
    agent_id: str
    risk_score: int
    risk_level: str
    contributing_signals: list[str] = Field(default_factory=list)
    total_actions: int = 0
    status: str = "nominal"


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
    "ReviewActionRequest",
    "ReviewActionResponse",
    "MetricsResponse",
    "AgentRiskResponse",
]
