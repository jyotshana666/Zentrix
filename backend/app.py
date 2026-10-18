from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from backend.database import (
    execute_action,
    get_agent_history,
    get_audit_log,
    get_db_fingerprint,
    get_transaction,
    init_db,
    log_event,
    reset_db,
)
from backend.policy_engine import (
    evaluate_action,
    get_task_policy,
    list_task_policies,
    register_task_policy,
)
from backend.schemas import (
    ActionRequest,
    DecisionResponse,
    EvaluateRequest,
    EvaluateResponse,
    TaskRegistrationRequest,
    TaskRegistrationResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and synthetic seed data on startup
    init_db()
    yield


app = FastAPI(
    title="Agent Warden-Z",
    description="Prototype API for agent action policy enforcement",
    version="0.1.0",
    lifespan=lifespan,
)


class AccessibleDict(dict):
    """Dict subclass providing attribute-style access for dictionary keys."""

    def __getattr__(self, name: str):
        try:
            val = self[name]
            if isinstance(val, dict) and not isinstance(val, AccessibleDict):
                val = AccessibleDict(val)
                self[name] = val
            return val
        except KeyError:
            raise AttributeError(f"'AccessibleDict' object has no attribute '{name}'")


# In-memory pending queue storing the request + response for each held action
# TODO: This in-memory pending queue will move to Member 3's SQLite store.
HELD_ACTIONS: list[dict] = []


@app.get("/health")
def health():
    return {"status": "ok", "service": "agent-warden-z"}


@app.post("/tasks", response_model=TaskRegistrationResponse)
def register_task(task: TaskRegistrationRequest):
    try:
        registered = register_task_policy(task)
        return TaskRegistrationResponse(
            task_id=task.task_id,
            status="registered",
            message=f"Task policy '{task.task_id}' registered successfully",
            policy=registered,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/tasks")
def get_all_tasks():
    return list_task_policies()


@app.get("/tasks/{task_id}")
def get_single_task(task_id: str):
    policy = get_task_policy(task_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Task policy not found")
    return {"task_id": task_id, "policy": policy}


@app.post("/actions/evaluate", response_model=DecisionResponse)
@app.post("/evaluate", response_model=DecisionResponse)
def evaluate(action: ActionRequest):
    response = evaluate_action(action)
    log_event(action, response, executed=False)

    if response.decision == "HOLD":
        HELD_ACTIONS.append(
            AccessibleDict({
                "request": AccessibleDict(action.model_dump() if hasattr(action, "model_dump") else action),
                "response": AccessibleDict(response.model_dump() if hasattr(response, "model_dump") else response),
            })
        )

    # This endpoint NEVER executes anything
    return response


@app.post("/actions/execute", response_model=DecisionResponse)
def execute(action: ActionRequest):
    try:
        response = evaluate_action(action)

        if response.decision == "ALLOW":
            ok = execute_action(action)
            response.executed = ok
        elif response.decision == "HOLD":
            HELD_ACTIONS.append(
                AccessibleDict({
                    "request": AccessibleDict(action.model_dump() if hasattr(action, "model_dump") else action),
                    "response": AccessibleDict(response.model_dump() if hasattr(response, "model_dump") else response),
                })
            )
        elif response.decision == "BLOCK":
            # Do not execute blocked actions
            pass

        log_event(action, response, executed=response.executed)
        return response
    except Exception:
        block_resp = DecisionResponse(
            action_id=getattr(action, "action_id", "unknown"),
            decision="BLOCK",
            reason="Gateway error - denied by default",
            risk_score=100,
            executed=False,
        )
        try:
            log_event(action, block_resp, executed=False)
        except Exception:
            pass
        return block_resp


@app.get("/actions/held")
def get_held():
    # TODO: This in-memory pending queue will move to Member 3's SQLite store.
    return HELD_ACTIONS


@app.get("/actions")
def get_actions(limit: int = 100):
    return get_audit_log(limit=limit)


@app.get("/agents/{agent_id}/history")
def get_agent_audit_history(agent_id: str):
    return get_agent_history(agent_id)


@app.get("/db/fingerprint")
def get_fingerprint():
    return {"fingerprint": get_db_fingerprint()}


@app.get("/db/transactions/{tx_id}")
def get_transaction_by_id(tx_id: str):
    tx = get_transaction(tx_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


# Demo-only endpoint: must be removed or protected in production
@app.post("/admin/reset")
def admin_reset():
    reset_db()
    HELD_ACTIONS.clear()
    return {"status": "reset"}
