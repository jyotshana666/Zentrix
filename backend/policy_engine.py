from __future__ import annotations
from typing import Any
from backend.schemas import (
    ActionRequest,
    DecisionResponse,
    EvaluateRequest,
    EvaluateResponse,
    TaskRegistrationRequest,
)

# Demo policies defining allowed operations, resources, and review triggers.
TASK_POLICIES: dict[str, dict[str, Any]] = {
    "task_read_transaction": {
        "purpose": "Investigate transaction status (read-only)",
        "allowed_operations": ["SELECT"],
        "allowed_resources": [
            "transactions",
            "transaction_tx1042",
            "transaction_tx1001",
            "transaction_tx1002",
            "transaction_tx1003",
        ],
        "requires_review_for": [],
    },
    "task_update_transaction": {
        "purpose": "Correct a transaction status with human review",
        "allowed_operations": ["SELECT"],
        "allowed_resources": [
            "transactions",
            "transaction_tx1042",
        ],
        "requires_review_for": ["UPDATE"],
    },
    "task_001": {
        "purpose": "Investigate transaction status (PRD demo read-only task)",
        "allowed_operations": ["SELECT"],
        "allowed_resources": [
            "transactions",
            "transaction_tx1042",
            "transaction_tx1001",
            "transaction_tx1002",
            "transaction_tx1003",
        ],
        "requires_review_for": [],
    },
    "task_002": {
        "purpose": "Report summary analysis",
        "allowed_operations": ["SELECT", "SUMMARIZE"],
        "allowed_resources": ["report_r001", "report_r002"],
        "requires_review_for": [],
    },
}


def _is_resource_allowed(resource: str, allowed_resources: list[str]) -> bool:
    """
    Check if a requested resource matches the permitted resources list.
    Supports exact matching and table/prefix matching (e.g. 'transaction_TX1042' matches 'transactions').
    """
    res = resource.strip().lower()
    for allowed in allowed_resources:
        allowed_norm = allowed.strip().lower()
        if res == allowed_norm:
            return True
        # Prefix matching between entity ID and table collection
        if allowed_norm in {"transactions", "transaction"} and res.startswith("transaction"):
            return True
        if allowed_norm in {"customers", "customer"} and res.startswith("customer"):
            return True
    return False


def register_task_policy(task: TaskRegistrationRequest | dict) -> dict[str, Any]:
    """Register or update a task policy dynamically."""
    if hasattr(task, "model_dump"):
        data = task.model_dump()
    elif isinstance(task, dict):
        data = task
    else:
        data = {
            "task_id": getattr(task, "task_id", ""),
            "purpose": getattr(task, "purpose", ""),
            "allowed_operations": getattr(task, "allowed_operations", ["SELECT"]),
            "allowed_resources": getattr(task, "allowed_resources", ["transactions"]),
            "requires_review_for": getattr(task, "requires_review_for", []),
        }

    task_id = str(data.get("task_id", "")).strip()
    if not task_id:
        raise ValueError("task_id is required")

    allowed_ops = []
    for op in data.get("allowed_operations", ["SELECT"]):
        cleaned = str(op).strip().upper()
        if cleaned == "READ":
            cleaned = "SELECT"
        elif cleaned == "WRITE":
            cleaned = "UPDATE"
        allowed_ops.append(cleaned)

    review_ops = []
    for op in data.get("requires_review_for", []):
        cleaned = str(op).strip().upper()
        if cleaned == "READ":
            cleaned = "SELECT"
        elif cleaned == "WRITE":
            cleaned = "UPDATE"
        review_ops.append(cleaned)

    allowed_res = [str(r).strip().lower() for r in data.get("allowed_resources", ["transactions"])]

    TASK_POLICIES[task_id] = {
        "purpose": data.get("purpose", ""),
        "allowed_operations": allowed_ops,
        "allowed_resources": allowed_res,
        "requires_review_for": review_ops,
    }
    return TASK_POLICIES[task_id]


def get_task_policy(task_id: str) -> dict[str, Any] | None:
    """Retrieve an active task policy by task_id."""
    return TASK_POLICIES.get(task_id)


def list_task_policies() -> dict[str, dict[str, Any]]:
    """Return all currently registered task policies."""
    return dict(TASK_POLICIES)


def evaluate_action(action: ActionRequest | EvaluateRequest) -> DecisionResponse:
    """
    Evaluate an action against configured task policies.

    Evaluation order:
      1. Unknown task -> BLOCK, "Unknown task", risk 100
      2. Normalize operation (strip + upper) and resource (strip + lower)
      3. Resource not in allowed_resources -> BLOCK, "Resource '<r>' is outside the task's permitted scope", risk 100
      4. Operation in requires_review_for -> HOLD, "Additional authorization required for <OP>", risk 60
      5. Operation not in allowed_operations -> BLOCK, "<OP> is not permitted by the task policy", risk 100
      6. Otherwise -> ALLOW, "Matches task policy", risk 0

    Fails closed on any exception (returns BLOCK, risk 100, executed False).
    """
    try:
        task_id = getattr(action, "task_id", None)
        action_id = getattr(action, "action_id", "unknown")

        # 1. Unknown task -> BLOCK, "Unknown task", risk 100
        policy = TASK_POLICIES.get(task_id)
        if policy is None:
            return DecisionResponse(
                action_id=action_id,
                decision="BLOCK",
                reason=f"Unknown task: {task_id}",
                risk_score=100,
                executed=False,
            )

        # 2. Normalize operation (strip + upper) and resource (strip + lower)
        raw_op = getattr(action, "operation", "")
        raw_res = getattr(action, "resource", "")
        op_clean = str(raw_op).strip().upper()
        if op_clean == "READ":
            op_clean = "SELECT"
        elif op_clean == "WRITE":
            op_clean = "UPDATE"

        resource = str(raw_res).strip().lower()

        allowed_resources = [r.strip().lower() for r in policy.get("allowed_resources", [])]
        requires_review_for = [op.strip().upper() for op in policy.get("requires_review_for", [])]
        allowed_operations = [op.strip().upper() for op in policy.get("allowed_operations", [])]

        # 3. Resource not in allowed_resources -> BLOCK
        if not _is_resource_allowed(resource, allowed_resources):
            return DecisionResponse(
                action_id=action_id,
                decision="BLOCK",
                reason=f"Resource '{resource}' is outside the task's permitted scope",
                risk_score=100,
                executed=False,
            )

        # 4. Operation in requires_review_for -> HOLD
        if op_clean in requires_review_for:
            return DecisionResponse(
                action_id=action_id,
                decision="HOLD",
                reason=f"Additional authorization required for {op_clean}",
                risk_score=60,
                executed=False,
            )

        # 5. Operation not in allowed_operations -> BLOCK
        if op_clean not in allowed_operations:
            return DecisionResponse(
                action_id=action_id,
                decision="BLOCK",
                reason=f"{op_clean} is not permitted by the task policy",
                risk_score=100,
                executed=False,
            )

        # 6. Otherwise -> ALLOW
        return DecisionResponse(
            action_id=action_id,
            decision="ALLOW",
            reason="Matches task policy",
            risk_score=0,
            executed=False,
        )
    except Exception as exc:
        # Fail-closed behavior: any exception -> BLOCK, executed stays False
        action_id = getattr(action, "action_id", "unknown")
        return DecisionResponse(
            action_id=action_id,
            decision="BLOCK",
            reason=f"Policy evaluation failure: {exc}",
            risk_score=100,
            executed=False,
        )


def apply_drift(
    decision_response: EvaluateResponse | DecisionResponse | dict,
    drift_score: int | None = None,
) -> EvaluateResponse:
    """
    Hook to combine Member 2's drift score into a policy decision.

    Rules:
      - If decision is already BLOCK, return it unchanged (explicit violations are never softened).
      - If decision is ALLOW and drift_score >= 60 -> upgrade to HOLD, reason "Elevated behavioral risk", risk_score = drift_score.
      - If decision is ALLOW and 30 <= drift_score < 60 -> stay ALLOW but set risk_score = drift_score.
      - A low drift score must never turn HOLD or BLOCK into ALLOW.
      - drift_score None -> return unchanged.
    """
    if isinstance(decision_response, dict):
        response_obj = EvaluateResponse(**decision_response)
    else:
        response_obj = decision_response

    if drift_score is None:
        return response_obj

    # If decision is already BLOCK, return it unchanged (explicit violations are never softened)
    if response_obj.decision == "BLOCK":
        return response_obj

    # A low drift score must never turn HOLD into ALLOW
    if response_obj.decision == "HOLD":
        return response_obj

    # If decision is ALLOW
    if response_obj.decision == "ALLOW":
        if drift_score >= 60:
            return EvaluateResponse(
                action_id=response_obj.action_id,
                decision="HOLD",
                reason="Elevated behavioral risk",
                risk_score=drift_score,
                executed=response_obj.executed,
            )
        elif 30 <= drift_score < 60:
            return EvaluateResponse(
                action_id=response_obj.action_id,
                decision="ALLOW",
                reason=response_obj.reason,
                risk_score=drift_score,
                executed=response_obj.executed,
            )
        else:
            return response_obj

    return response_obj


__all__ = [
    "TASK_POLICIES",
    "evaluate_action",
    "apply_drift",
    "register_task_policy",
    "get_task_policy",
    "list_task_policies",
]
