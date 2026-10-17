
from backend.schemas import ActionRequest, DecisionResponse


# Initial demo policy. We will make task scopes configurable later.
TASK_POLICIES = {
    "task_read_transaction": {
        "operations": {"SELECT"},
        "resources": {"transactions"},
    }
}


def evaluate_action(action: ActionRequest) -> DecisionResponse:
    policy = TASK_POLICIES.get(action.task_id)

    if policy is None:
        return DecisionResponse(
            action_id=action.action_id,
            decision="BLOCK",
            reason="Unknown task: no policy is defined",
            risk_score=100,
            executed=False,
        )

    if action.operation not in policy["operations"]:
        return DecisionResponse(
            action_id=action.action_id,
            decision="BLOCK",
            reason="Operation is outside the task's permitted scope",
            risk_score=100,
            executed=False,
        )

    if action.resource not in policy["resources"]:
        return DecisionResponse(
            action_id=action.action_id,
            decision="BLOCK",
            reason="Resource is outside the task's permitted scope",
            risk_score=100,
            executed=False,
        )

    return DecisionResponse(
        action_id=action.action_id,
        decision="ALLOW",
        reason="Operation and resource match the task policy",
        risk_score=0,
        executed=False,
    )
