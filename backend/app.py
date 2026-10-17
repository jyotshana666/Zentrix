
from fastapi import FastAPI

from backend.policy_engine import evaluate_action
from backend.schemas import ActionRequest, DecisionResponse

app = FastAPI(
    title="Agent Warden-Z",
    description="Prototype API for agent action policy enforcement",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "agent-warden-z"}


@app.post("/evaluate", response_model=DecisionResponse)
def evaluate(action: ActionRequest):
    return evaluate_action(action)
