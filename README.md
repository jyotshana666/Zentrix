# Agent Warden-Z

**IBM Z Datathon 2026 — Theme: AI Secured — Innovation Without Exposure**

Agent Warden-Z evaluates requested actions from AI agents, detects suspicious behavioral drift, and assists the policy gateway in making ALLOW, HOLD, or BLOCK decisions before any database execution occurs.

## System Flow

```
Request
  → API Gateway
  → Policy Validation
  → Behavioral Drift & Risk Assessment   ← (this repo's drift module)
  → ALLOW / HOLD / BLOCK decision
  → Controlled Database Executor (only when allowed)
  → Audit Log
  → Dashboard
```

## Modules

| Module | Owner Role | Status |
|--------|-----------|--------|
| `drift/` | Behavioral Drift & Synthetic Data Lead | In progress |
| `gateway/` | API Gateway | Pending |
| `policy/` | Policy Engine | Pending |
| `executor/` | Database Executor | Pending |

## Shared Action Request Schema

```json
{
  "action_id": "act_001",
  "agent_id": "agent_01",
  "session_id": "session_01",
  "task_id": "task_001",
  "operation": "UPDATE",
  "resource": "transaction_TX1042"
}
```

## Shared Response Schema

```json
{
  "action_id": "act_001",
  "decision": "BLOCK",
  "reason": "Write is outside the declared task scope",
  "risk_score": 35,
  "executed": false
}
```

Valid decisions: `ALLOW`, `HOLD`, `BLOCK`

## Important Constraints

- The **policy engine** is the authoritative source for ALLOW/HOLD/BLOCK decisions.
- A risk score **never** grants permissions or overrides a prohibited action.
- No real customer data, secrets, or credentials are used — synthetic data only.
- No database writes are executed by the drift module.

## Setup

```bash
pip install pytest
python drift/generate_data.py   # generate synthetic scenarios
pytest tests/                   # run all tests
```

## Branches

- `main` — shared integration branch
- `feature/behavioral-drift` — Behavioral Drift & Synthetic Data Lead's work
