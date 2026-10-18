
from backend.schemas import (
    ActionRequest,
    DecisionResponse,
    EvaluateRequest,
    EvaluateResponse,
)

# Demo policies defining allowed operations, resources, and review triggers.
TASK_POLICIES = {
    "task_read_transaction": {
        "allowed_operations": ["SELECT"],
        "allowed_resources": ["transactions"],
        "requires_review_for": ["UPDATE", "DELETE"],
    },
    "task_update_transaction": {
        "allowed_operations": ["SELECT"],
        "allowed_resources": ["transactions"],
        "requires_review_for": ["UPDATE"],
    },
}


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
                reason="Unknown task",
                risk_score=100,
                executed=False,
            )

        # 2. Normalize operation (strip + upper) and resource (strip + lower)
        raw_op = getattr(action, "operation", "")
        raw_res = getattr(action, "resource", "")
        operation = raw_op.strip().upper() if isinstance(raw_op, str) else str(raw_op).strip().upper()
        resource = raw_res.strip().lower() if isinstance(raw_res, str) else str(raw_res).strip().lower()

        allowed_resources = [r.strip().lower() for r in policy.get("allowed_resources", [])]
        requires_review_for = [op.strip().upper() for op in policy.get("requires_review_for", [])]
        allowed_operations = [op.strip().upper() for op in policy.get("allowed_operations", [])]

        # 3. Resource not in allowed_resources -> BLOCK
        if resource not in allowed_resources:
            return DecisionResponse(
                action_id=action_id,
                decision="BLOCK",
                reason=f"Resource '{resource}' is outside the task's permitted scope",
                risk_score=100,
                executed=False,
            )

        # 4. Operation in requires_review_for -> HOLD
        if operation in requires_review_for:
            return DecisionResponse(
                action_id=action_id,
                decision="HOLD",
                reason=f"Additional authorization required for {operation}",
                risk_score=60,
                executed=False,
            )

        # 5. Operation not in allowed_operations -> BLOCK
        if operation not in allowed_operations:
            return DecisionResponse(
                action_id=action_id,
                decision="BLOCK",
                reason=f"{operation} is not permitted by the task policy",
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

    Args:
        decision_response: The policy decision response (EvaluateResponse / DecisionResponse or dict).
        drift_score: Optional behavioral drift score (0-100) provided by Member 2.

    Returns:
        EvaluateResponse: The combined evaluation response.
    """
    if isinstance(decision_response, dict):
        response_obj = EvaluateResponse(**decision_response)
    else:
        response_obj = decision_response

    # drift_score None -> return unchanged
    if drift_score is None:
        return response_obj

    # If decision is already BLOCK, return it unchanged (explicit violations are never softened)
    if response_obj.decision == "BLOCK":
        return response_obj

    # A low drift score must never turn HOLD or BLOCK into ALLOW
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
]
