
from fastapi import FastAPI

from backend.policy_engine import evaluate_action
from backend.schemas import (
    ActionRequest,
    DecisionResponse,
    EvaluateRequest,
    EvaluateResponse,
)

app = FastAPI(
    title="Agent Warden-Z",
    description="Prototype API for agent action policy enforcement",
    version="0.1.0",
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


@app.post("/evaluate", response_model=DecisionResponse)
def evaluate(action: ActionRequest):
    return evaluate_action(action)


@app.post("/actions/execute", response_model=DecisionResponse)
def execute_action(action: ActionRequest):
    decision = evaluate_action(action)

    if decision.decision == "HOLD":
        HELD_ACTIONS.append(
            AccessibleDict({
                "request": AccessibleDict(action.model_dump() if hasattr(action, "model_dump") else action),
                "response": AccessibleDict(decision.model_dump() if hasattr(decision, "model_dump") else decision),
            })
        )
        return decision

    if decision.decision == "BLOCK":
        return decision

    # If decision == ALLOW:
    # TODO: call Member 3's controlled executor here, then set executed=True only after it confirms
    return decision


@app.get("/actions/held")
def get_held():
    # TODO: This in-memory pending queue will move to Member 3's SQLite store.
    return HELD_ACTIONS
