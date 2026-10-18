"""
backend/drift.py
================
Intent-Aware Behavioral Drift Risk Scorer for Agent Warden-Z.
Implements the PRD Section 7.5 behavioral drift formula:

    R = min(100, 25*U + 20*W + 15*P + 10*D)

where:
  - U: Unrelated-resource access signal (weight 25)
  - W: Unexpected write-operation signal (weight 20)
  - P: Privilege / operation escalation signal (weight 15)
  - D: Repeated denied or out-of-scope attempts signal (weight 10 per denial / session)

This module satisfies the shared schema requirements and integrates Member 2's
drift assessment into the primary gateway execution pipeline.
"""

from __future__ import annotations

from typing import Any


HIGH_RISK_OPS = {"DELETE", "DROP", "TRUNCATE", "EXPORT", "EXFILTRATE"}
WRITE_OPS = {"UPDATE", "INSERT", "WRITE", "MODIFY", "PATCH"}
READ_OPS = {"SELECT", "READ", "QUERY", "GET"}


def compute_drift_score(agent_id: str, history: list[dict[str, Any]] | None) -> int:
    """
    Compute behavioral drift score for an agent from its action history.
    Formula: R = min(100, 25*U + 20*W + 15*P + 10*D)

    Args:
        agent_id: The ID of the agent to evaluate.
        history: Flat list of historical action/audit dictionaries.

    Returns:
        int: Risk score bounded in [0, 100].
    """
    try:
        if not isinstance(agent_id, str) or not agent_id.strip():
            return 0
        if not isinstance(history, list) or len(history) == 0:
            return 0

        target_agent = agent_id.strip()

        # Filter strictly to target agent's actions
        agent_events = [
            e for e in history
            if isinstance(e, dict) and str(e.get("agent_id", "")).strip() == target_agent
        ]

        if not agent_events:
            return 0

        # Signals
        has_unrelated_resource = False
        has_unexpected_write = False
        has_privilege_escalation = False
        denial_count = 0
        blocked_sessions: set[str] = set()

        for event in agent_events:
            raw_op = str(event.get("operation", "")).strip().upper()
            raw_res = str(event.get("resource", "")).strip().lower()
            reason = str(event.get("reason", "")).strip().lower()

            # Normalise decision (support both 'decision' and 'policy_decision')
            decision = str(event.get("decision") or event.get("policy_decision") or "").strip().upper()
            session_id = str(event.get("session_id", "")).strip()

            if decision == "BLOCK":
                denial_count += 1
                if session_id:
                    blocked_sessions.add(session_id)

            # U: Unrelated-resource access signal
            if (
                "resource" in reason and ("outside" in reason or "permitted" in reason or "unrelated" in reason)
                or raw_res in {"secrets", "customer_credit_cards", "auth_tokens", "audit_log", "unrelated"}
                or "customer" in raw_res and "transaction" in str(event.get("task_id", "")).lower()
            ):
                has_unrelated_resource = True

            # W: Unexpected write operation signal
            if raw_op in WRITE_OPS:
                has_unexpected_write = True

            # P: Privilege or operation escalation signal
            if (
                raw_op in HIGH_RISK_OPS
                or "privilege" in reason
                or "escalation" in reason
                or "export" in reason
                or "exfiltrat" in reason
            ):
                has_privilege_escalation = True

        # Compute signals according to PRD formula
        u_val = 1 if has_unrelated_resource else 0
        w_val = 1 if has_unexpected_write else 0
        p_val = 1 if has_privilege_escalation else 0

        # D: Repeated denials. Use denial count (or session count if available)
        d_val = denial_count

        raw_score = (25 * u_val) + (20 * w_val) + (15 * p_val) + (10 * d_val)
        score = min(100, max(0, raw_score))
        return score

    except Exception:
        # Failsafe: never raise
        return 0


def assess_agent_risk(agent_id: str, history: list[dict[str, Any]] | None) -> dict[str, Any]:
    """
    Return comprehensive risk analysis for an agent suitable for API response
    and frontend dashboard consumption.
    """
    score = compute_drift_score(agent_id, history)

    if score <= 29:
        level = "LOW"
    elif score <= 59:
        level = "MEDIUM"
    else:
        level = "HIGH"

    contributing_signals = []
    if history:
        for event in history:
            if not isinstance(event, dict):
                continue
            if str(event.get("agent_id", "")).strip() != agent_id:
                continue
            op = str(event.get("operation", "")).strip().upper()
            dec = str(event.get("decision") or event.get("policy_decision") or "").strip().upper()
            if dec == "BLOCK":
                contributing_signals.append(f"Denied action {event.get('action_id', 'unknown')}: {event.get('reason', 'Policy block')}")
            if op in HIGH_RISK_OPS:
                contributing_signals.append(f"High-risk operation attempted: {op}")
            elif op in WRITE_OPS:
                contributing_signals.append(f"Write operation attempted: {op}")

    # Deduplicate signals
    signals_dedup = list(dict.fromkeys(contributing_signals))

    return {
        "agent_id": agent_id,
        "risk_score": score,
        "risk_level": level,
        "contributing_signals": signals_dedup,
        "total_actions": len([e for e in (history or []) if isinstance(e, dict) and str(e.get("agent_id", "")).strip() == agent_id]),
        "status": "elevated_risk" if score >= 60 else ("moderate_risk" if score >= 30 else "nominal"),
    }


__all__ = ["compute_drift_score", "assess_agent_risk"]
