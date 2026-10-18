import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.database import (
    compute_system_metrics,
    execute_action,
    get_agent_history,
    get_audit_log,
    get_db_fingerprint,
    get_held_actions,
    get_transaction,
    init_db,
    log_event,
    reset_db,
    resolve_held_action,
    save_held_action,
)
from backend.drift import assess_agent_risk, compute_drift_score
from backend.policy_engine import (
    apply_drift,
    evaluate_action,
    get_task_policy,
    list_task_policies,
    register_task_policy,
)
from backend.schemas import (
    ActionRequest,
    AgentRiskResponse,
    DecisionResponse,
    EvaluateRequest,
    EvaluateResponse,
    MetricsResponse,
    ReviewActionRequest,
    ReviewActionResponse,
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
    description="Intent-Aware Security Gateway for AI Agent Database Operations",
    version="1.0.0",
    lifespan=lifespan,
)

# Trusted origins for Warden-Z dashboard and local dev environments
DEFAULT_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]


def get_allowed_origins() -> list[str]:
    raw = os.getenv("WARDEN_ALLOWED_ORIGINS", "")
    if raw.strip():
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return list(DEFAULT_TRUSTED_ORIGINS)


ALLOWED_ORIGINS = get_allowed_origins()

# Enable CORS restricted to trusted frontend origins with credential handling
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
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


# In-memory pending queue mirror for backward compatibility with existing tests
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
    # 1. Deterministic task policy evaluation
    response = evaluate_action(action)

    # 2. Behavioral drift assessment across prior sessions
    try:
        history = get_agent_history(action.agent_id)
        drift_score = compute_drift_score(action.agent_id, history)
        response = apply_drift(response, drift_score)
    except Exception:
        # Non-blocking drift calculation fallback
        pass

    # 3. Log event into audit store (evaluate endpoint never executes DB operations)
    log_event(action, response, executed=False)

    if response.decision == "HOLD":
        save_held_action(action, response)
        HELD_ACTIONS.append(
            AccessibleDict({
                "request": AccessibleDict(action.model_dump() if hasattr(action, "model_dump") else action),
                "response": AccessibleDict(response.model_dump() if hasattr(response, "model_dump") else response),
            })
        )

    return response


@app.post("/actions/execute", response_model=DecisionResponse)
def execute(action: ActionRequest):
    try:
        # 1. Deterministic task policy evaluation
        response = evaluate_action(action)

        # 2. Behavioral drift assessment across prior sessions
        history = get_agent_history(action.agent_id)
        drift_score = compute_drift_score(action.agent_id, history)
        response = apply_drift(response, drift_score)

        # 3. Controlled enforcement
        if response.decision == "ALLOW":
            ok = execute_action(action)
            response.executed = ok
        elif response.decision == "HOLD":
            response.executed = False
            save_held_action(action, response)
            HELD_ACTIONS.append(
                AccessibleDict({
                    "request": AccessibleDict(action.model_dump() if hasattr(action, "model_dump") else action),
                    "response": AccessibleDict(response.model_dump() if hasattr(response, "model_dump") else response),
                })
            )
        elif response.decision == "BLOCK":
            # Hard stop: do not execute blocked actions
            response.executed = False

        # 4. Audit logging with verified execution status
        log_event(action, response, executed=response.executed)
        return response

    except Exception:
        # Fail-closed: return authoritative BLOCK
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
    db_held = get_held_actions(status="PENDING")
    if db_held:
        return [
            AccessibleDict({
                "request": AccessibleDict(row),
                "response": AccessibleDict({
                    "action_id": row["action_id"],
                    "decision": row["decision"],
                    "reason": row["reason"],
                    "risk_score": row["risk_score"],
                    "executed": False,
                }),
            })
            for row in db_held
        ]
    return HELD_ACTIONS


@app.post("/reviews/{action_id}", response_model=ReviewActionResponse)
def review_action(action_id: str, review: ReviewActionRequest):
    result = resolve_held_action(
        action_id=action_id,
        decision=review.decision,
        reviewer_id=review.reviewer_id,
        notes=review.notes,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Held action '{action_id}' not found")

    # Update in-memory mirror if present
    global HELD_ACTIONS
    HELD_ACTIONS = [h for h in HELD_ACTIONS if h.get("request", {}).get("action_id") != action_id]

    return ReviewActionResponse(
        action_id=action_id,
        status=result["status"],
        decision=result["decision"],
        executed=result["executed"],
        message=f"Action '{action_id}' {result['status'].lower()} by reviewer '{review.reviewer_id}'",
    )


@app.get("/actions")
def get_actions(limit: int = 100):
    return get_audit_log(limit=limit)


@app.get("/agents/{agent_id}/history")
def get_agent_audit_history(agent_id: str):
    return get_agent_history(agent_id)


@app.get("/agents/{agent_id}/risk", response_model=AgentRiskResponse)
def get_agent_behavioral_risk(agent_id: str):
    history = get_agent_history(agent_id)
    risk_info = assess_agent_risk(agent_id, history)
    return AgentRiskResponse(**risk_info)


@app.get("/metrics", response_model=MetricsResponse)
def get_system_metrics():
    metrics = compute_system_metrics()
    return MetricsResponse(**metrics)


@app.get("/db/fingerprint")
def get_fingerprint():
    return {"fingerprint": get_db_fingerprint()}


@app.get("/db/transactions/{tx_id}")
def get_transaction_by_id(tx_id: str):
    tx = get_transaction(tx_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


# Demo-only endpoint: reset database and held queues for clean test reruns
@app.post("/admin/reset")
def admin_reset():
    reset_db()
    HELD_ACTIONS.clear()
    return {"status": "reset"}
