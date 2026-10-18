"""
drift/risk_score.py
===================
Explainable, deterministic, rule-based behavioural drift risk scorer
for Agent Warden-Z.

Purpose:
    Assess how risky the current agent action is by combining:
      1. Policy outcome (was this action blocked by the policy engine?)
      2. Operation sensitivity (is this a write / export / delete?)
      3. Session-level anomaly (does this session break the baseline?)
      4. Cross-session repetition (has this agent been blocked before?)

Score range: 0 – 100
Risk levels:
    LOW    0 – 29
    MEDIUM 30 – 59
    HIGH   60 – 100

Important constraints:
    - The scorer does NOT grant or revoke permissions.
    - A low score NEVER makes a prohibited action permissible.
    - Policy violations remain visible even when the drift score is low.
    - The score is deterministic: same input → same output, always.
    - "Unusual but permitted" actions are not treated as policy violations.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Scoring configuration
# All weights and thresholds are collected here for easy adjustment.
# ---------------------------------------------------------------------------
SCORE_CONFIG = {
    # Added when the policy engine blocked the current action
    "policy_block_weight": 30,

    # Added for high-risk operation types (irreversible or data-leaking)
    "high_risk_ops": {"DELETE", "DROP", "TRUNCATE", "EXPORT", "EXFILTRATE"},
    "high_risk_op_weight": 20,

    # Added for medium-risk operation types (writes that are not deletes)
    "medium_risk_ops": {"UPDATE", "INSERT", "WRITE", "MODIFY", "PATCH"},
    "medium_risk_op_weight": 10,

    # Added per prior session that contained at least one blocked action
    "prior_block_weight": 10,

    # Cap on how much prior-session penalties can contribute
    "prior_block_max": 30,

    # Added when the current session's operation types differ from all
    # prior sessions for the same agent (baseline deviation)
    "baseline_deviation_weight": 5,

    # Risk level bands (prototype thresholds — not validated standards)
    "low_max": 29,
    "medium_max": 59,
}


# ---------------------------------------------------------------------------
# High-level types (plain dicts — no external dependencies needed)
# ---------------------------------------------------------------------------
# An action record matches the shared action-request schema:
# {
#     "action_id": str,
#     "agent_id":  str,
#     "session_id": str,
#     "task_id":   str,
#     "operation": str,
#     "resource":  str,
# }
#
# A policy result is whatever the policy engine returns; we only need:
# {
#     "decision": "ALLOW" | "HOLD" | "BLOCK",
#     ... (other fields are ignored by the scorer)
# }


def _risk_level(score: int) -> str:
    """Translate a numeric score into a human-readable risk level."""
    if score <= SCORE_CONFIG["low_max"]:
        return "LOW"
    if score <= SCORE_CONFIG["medium_max"]:
        return "MEDIUM"
    return "HIGH"


def calculate_risk_score(
    action: dict,
    policy_result: dict,
    session_history,          # SessionHistory instance (or None)
) -> dict:
    """
    Calculate a deterministic risk score for a single agent action.

    Args:
        action:         The current action record (shared schema fields).
        policy_result:  The policy engine's result for this action.
                        Must contain at least {"decision": "ALLOW"|"HOLD"|"BLOCK"}.
                        Pass {} or None if the policy result is not yet available.
        session_history: A SessionHistory instance populated with prior events.
                         Pass None for a fresh agent with no history.

    Returns:
        A dict with the following fields:
        {
            "agent_id":    str,
            "session_id":  str,
            "action_id":   str,
            "risk_score":  int,      # 0 – 100
            "risk_level":  str,      # LOW | MEDIUM | HIGH
            "reasons":     list[str] # Human-readable explanation of each signal
        }
    """
    # ------------------------------------------------------------------
    # Validate and normalise input
    # ------------------------------------------------------------------
    if not isinstance(action, dict):
        return _error_result("action must be a dict.")

    agent_id = str(action.get("agent_id", "")).strip()
    session_id = str(action.get("session_id", "")).strip()
    action_id = str(action.get("action_id", "unknown")).strip()
    operation = str(action.get("operation", "")).strip().upper()

    if not agent_id:
        return _error_result("action.agent_id is missing or empty.")
    if not operation:
        return _error_result("action.operation is missing or empty.")

    if policy_result is None:
        policy_result = {}

    decision = str(policy_result.get("decision", "")).strip().upper()

    score = 0
    reasons: list[str] = []

    # ------------------------------------------------------------------
    # Rule 1 — Policy block
    # If the policy engine blocked this action, that is the strongest
    # single signal.  A risk score does not override this decision.
    # ------------------------------------------------------------------
    if decision == "BLOCK":
        score += SCORE_CONFIG["policy_block_weight"]
        reasons.append(
            f"Policy engine blocked this action (decision=BLOCK, +{SCORE_CONFIG['policy_block_weight']} pts)."
        )
    elif decision == "HOLD":
        # HOLD carries half the penalty of a full block
        hold_weight = SCORE_CONFIG["policy_block_weight"] // 2
        score += hold_weight
        reasons.append(
            f"Policy engine placed this action on HOLD (+{hold_weight} pts)."
        )
    elif decision == "ALLOW":
        reasons.append("Policy engine allowed this action (no policy penalty).")
    else:
        # Policy result missing or unrecognised — flag it but do not assume safe
        reasons.append(
            "Policy decision not available; treating as unverified "
            "(no policy penalty applied, but this is not confirmation of safety)."
        )

    # ------------------------------------------------------------------
    # Rule 2 — Operation sensitivity
    # High-risk operations (exports, deletes) get a larger penalty than
    # medium-risk writes.  Reads carry no penalty on their own.
    # "Unusual but permitted" operations score only on their operation type,
    # not as a policy violation.
    # ------------------------------------------------------------------
    if operation in SCORE_CONFIG["high_risk_ops"]:
        score += SCORE_CONFIG["high_risk_op_weight"]
        reasons.append(
            f"Operation '{operation}' is high-risk (irreversible or data-leaking, "
            f"+{SCORE_CONFIG['high_risk_op_weight']} pts)."
        )
    elif operation in SCORE_CONFIG["medium_risk_ops"]:
        score += SCORE_CONFIG["medium_risk_op_weight"]
        reasons.append(
            f"Operation '{operation}' is a write-type operation "
            f"(+{SCORE_CONFIG['medium_risk_op_weight']} pts)."
        )
    else:
        reasons.append(f"Operation '{operation}' carries no inherent sensitivity penalty.")

    # ------------------------------------------------------------------
    # Rule 3 — Cross-session repetition of blocks
    # If this agent has been blocked in prior sessions, each blocked
    # session adds a penalty (capped at prior_block_max).
    # ------------------------------------------------------------------
    prior_block_sessions = 0
    prior_session_ops: set[str] = set()

    if session_history is not None and session_id:
        try:
            past_sessions = session_history.get_past_sessions(
                agent_id=agent_id,
                before_session_id=session_id,
            )
        except Exception:
            past_sessions = {}

        for sid, events in past_sessions.items():
            session_ops = {str(e.get("operation", "")).upper() for e in events}
            prior_session_ops.update(session_ops)

            # A session "contained a block" if any event has policy_decision BLOCK,
            # or if any event's operation is in the high/medium risk sets
            # and was not explicitly allowed.
            session_was_blocked = any(
                str(e.get("policy_decision", "")).upper() == "BLOCK"
                for e in events
            )
            if session_was_blocked:
                prior_block_sessions += 1

    if prior_block_sessions > 0:
        penalty = min(
            prior_block_sessions * SCORE_CONFIG["prior_block_weight"],
            SCORE_CONFIG["prior_block_max"],
        )
        score += penalty
        reasons.append(
            f"Agent was blocked in {prior_block_sessions} prior session(s) "
            f"(+{penalty} pts — escalation signal)."
        )
    elif session_history is not None:
        reasons.append("No prior blocked sessions found for this agent.")

    # ------------------------------------------------------------------
    # Rule 4 — Baseline deviation
    # If the current operation type has never appeared in any prior session
    # for this agent, it is a behavioural change — a weak signal.
    # Note: this is a deviation signal, NOT a policy violation.
    # ------------------------------------------------------------------
    if session_history is not None and prior_session_ops and session_id:
        if operation not in prior_session_ops:
            score += SCORE_CONFIG["baseline_deviation_weight"]
            reasons.append(
                f"Operation '{operation}' has not appeared in this agent's "
                f"prior sessions (baseline deviation, "
                f"+{SCORE_CONFIG['baseline_deviation_weight']} pts). "
                f"This is a drift signal, not a policy violation."
            )
        else:
            reasons.append(
                f"Operation '{operation}' is consistent with the agent's baseline."
            )

    # ------------------------------------------------------------------
    # Clamp score to [0, 100]
    # ------------------------------------------------------------------
    score = max(0, min(100, score))

    return {
        "agent_id": agent_id,
        "session_id": session_id,
        "action_id": action_id,
        "risk_score": score,
        "risk_level": _risk_level(score),
        "reasons": reasons,
    }


def _error_result(message: str) -> dict:
    """Return a safe error result when input is invalid."""
    return {
        "agent_id": "unknown",
        "session_id": "unknown",
        "action_id": "unknown",
        "risk_score": 0,
        "risk_level": "LOW",
        "reasons": [f"[INPUT ERROR] {message} Risk score is 0 but this does NOT "
                    "confirm the action is safe — the policy engine must decide."],
    }


# ---------------------------------------------------------------------------
# Quick demonstration — run: python -m drift.risk_score
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from drift.generate_data import generate_scenarios
    from drift.session_history import SessionHistory

    scenarios = generate_scenarios()

    # Load ALL events into a shared history so we can test cross-session scoring
    history = SessionHistory()
    history.add_events(scenarios)

    print("=" * 70)
    print("RISK SCORE DEMONSTRATION — Agent Warden-Z")
    print("=" * 70)

    # Score each scenario as if it were the current action being evaluated
    for scenario in scenarios:
        # Simulate a policy result from the synthetic label
        policy_decision = scenario.get("policy_decision", "ALLOW")
        policy_result = {"decision": policy_decision}

        # Use a fresh history per evaluation that includes only events
        # from BEFORE the current action in insertion order.
        # For demonstration we use the full shared history.
        result = calculate_risk_score(scenario, policy_result, history)

        print(f"\n{scenario['action_id']} | {scenario['agent_id']} | "
              f"{scenario['session_id']} | op={scenario['operation']} | "
              f"label={scenario.get('label')}")
        print(f"  Risk Score : {result['risk_score']} ({result['risk_level']})")
        for r in result["reasons"]:
            print(f"  • {r}")
