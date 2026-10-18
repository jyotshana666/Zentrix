"""
drift/drift_assessor.py
=======================
Public integration interface for the Agent Warden-Z drift module.

Purpose:
    Expose easy-to-call functions that teammates or the API gateway
    can use to request a drift assessment for any agent action.

Public API
----------
compute_drift_score(agent_id, history) -> int
    Teammate-facing function.  Accepts an agent ID and a flat list of
    historical action dicts.  Returns a single integer 0–100.

    from drift.drift_assessor import compute_drift_score
    score = compute_drift_score("agent_01", list_of_action_dicts)

assess_drift(action, policy_result, session_history) -> dict
    Full drift assessment dict including reasons and risk level.

build_response(action, policy_result, drift_result) -> dict
    Merges policy + drift into the shared gateway response schema.

Scoring rules (transparent, configurable via drift.risk_score.SCORE_CONFIG)
---------------------------------------------------------------------------
  Rule 1 — Policy decision
      BLOCK  → +30 pts        (strongest signal)
      HOLD   → +15 pts
      ALLOW  →  +0 pts
  Rule 2 — Operation sensitivity
      High-risk (DELETE, DROP, TRUNCATE, EXPORT, EXFILTRATE) → +20 pts
      Medium-risk (UPDATE, INSERT, WRITE, MODIFY, PATCH)     → +10 pts
      Read-only (READ, etc.)                                  →  +0 pts
  Rule 3 — Cross-session repetition of blocks
      +10 pts per prior session that contained a BLOCK (capped at +30)
  Rule 4 — Baseline deviation
      Operation never seen in prior sessions → +5 pts (drift signal, not a violation)

Important constraints:
    - This module DOES NOT grant or revoke permissions.
    - The policy engine remains the authoritative source for ALLOW/HOLD/BLOCK.
    - This module DOES NOT execute any database operations.
    - A low risk score does NOT make a prohibited action permissible.
    - Unusual-but-permitted actions are NOT treated as policy violations.
"""

from __future__ import annotations

from drift.risk_score import calculate_risk_score
from drift.session_history import SessionHistory


# ---------------------------------------------------------------------------
# Primary public function
# ---------------------------------------------------------------------------

def assess_drift(
    action: dict,
    policy_result: dict,
    session_history: "SessionHistory | None" = None,
) -> dict:
    """
    Assess behavioural drift for a single agent action.

    Args:
        action:          Current action record (shared schema fields required):
                         action_id, agent_id, session_id, task_id,
                         operation, resource.
        policy_result:   Result from the policy engine.
                         Must contain {"decision": "ALLOW"|"HOLD"|"BLOCK"}.
                         Pass {} or None if not yet available.
        session_history: A populated SessionHistory instance.
                         Pass None if the agent has no prior history.

    Returns:
        Dict with drift assessment fields:
        {
            "agent_id":   str,
            "session_id": str,
            "action_id":  str,
            "risk_score": int,      # 0–100
            "risk_level": str,      # LOW | MEDIUM | HIGH
            "reasons":    list[str]
        }

    Note:
        The returned dict does NOT contain a "decision" field.
        Decision-making remains with the policy engine / API gateway.
    """
    return calculate_risk_score(action, policy_result, session_history)


# ---------------------------------------------------------------------------
# Helper: merge drift result into the shared gateway response format
# ---------------------------------------------------------------------------

def build_response(
    action: dict,
    policy_result: dict,
    drift_result: dict,
) -> dict:
    """
    Merge the policy result and drift assessment into the shared response schema.

    Shared response schema:
    {
        "action_id": str,
        "decision":  "ALLOW" | "HOLD" | "BLOCK",
        "reason":    str,
        "risk_score": int,
        "executed":  bool,
    }

    Extended fields added by the drift module:
        "risk_level":  str       — LOW | MEDIUM | HIGH
        "drift_reasons": list[str] — per-rule explanations

    Args:
        action:       The original action request dict.
        policy_result: The policy engine's decision dict.
        drift_result:  Output of assess_drift().

    Returns:
        A response dict compatible with the shared schema plus drift fields.
    """
    decision = str(policy_result.get("decision", "HOLD")).upper()

    # The primary reason comes from the policy engine if available;
    # fall back to the top drift reason.
    policy_reason = policy_result.get("reason", "")
    if not policy_reason and drift_result.get("reasons"):
        policy_reason = drift_result["reasons"][0]

    return {
        # ── Shared schema fields ───────────────────────────────────────
        "action_id":  action.get("action_id", "unknown"),
        "decision":   decision,
        "reason":     policy_reason,
        "risk_score": drift_result.get("risk_score", 0),
        "executed":   False,          # Drift module never executes DB operations

        # ── Extended drift fields (do not conflict with shared schema) ─
        "risk_level":     drift_result.get("risk_level", "LOW"),
        "drift_reasons":  drift_result.get("reasons", []),

        # ── Agent context ──────────────────────────────────────────────
        "agent_id":   drift_result.get("agent_id", action.get("agent_id", "unknown")),
        "session_id": drift_result.get("session_id", action.get("session_id", "unknown")),
    }


# ---------------------------------------------------------------------------
# Convenience: pre-built SessionHistory for the synthetic dataset
# (useful for testing without wiring up a live event store)
# ---------------------------------------------------------------------------

def build_demo_history() -> SessionHistory:
    """
    Return a SessionHistory pre-loaded with the synthetic dataset.

    Use this for local testing only.  In production, the caller should
    manage and pass in a SessionHistory populated from the live event store.
    """
    from drift.generate_data import generate_scenarios
    history = SessionHistory()
    history.add_events(generate_scenarios())
    return history


# ---------------------------------------------------------------------------
# Teammate-facing integration function
# ---------------------------------------------------------------------------

def compute_drift_score(agent_id: str, history: list[dict]) -> int:
    """
    Compute a behavioral drift score for an agent from its action history.

    This is the primary function called by the policy engine integration.
    The policy engine passes the returned integer to apply_drift(response, drift_score).

    Args:
        agent_id (str):
            The ID of the agent to score.  Only actions belonging to this
            agent are considered.  Actions for other agents in the list are
            silently ignored — histories are never mixed.

        history (list[dict]):
            A flat list of historical action dictionaries in the format used
            by the shared action-request schema:

                {
                    "action_id":       str,  # unique action identifier
                    "agent_id":        str,  # must match the agent_id arg to count
                    "session_id":      str,  # groups events into sessions
                    "task_id":         str,  # (optional but recommended)
                    "operation":       str,  # e.g. READ, UPDATE, DELETE, EXPORT
                    "resource":        str,  # e.g. transaction_TX1042
                    "policy_decision": str,  # optional: "ALLOW" or "BLOCK"
                }

            Records missing required fields are skipped without raising.
            An empty list or a list with no matching agent_id returns 0.

    Returns:
        int: Behavioral drift score in the range [0, 100] (inclusive).
             0   = no drift signals detected (low risk).
             100 = maximum drift signal (high risk).
             The same inputs always produce the same score (deterministic).

    Scoring rules (see module docstring for full detail):
        - Each session that contained a BLOCK contributes to the score.
        - Sensitive operations (DELETE, EXPORT, UPDATE …) increase the score.
        - Unusual-but-permitted operations produce only a small deviation signal.
        - Normal permitted reads produce a score of 0.

    Integration note:
        This function only calculates and returns a score.
        It does NOT change any decision, execute database operations, or
        authorize/prohibit any action.  Those responsibilities remain with
        the policy engine via apply_drift().

    Session ordering guarantee:
        Events are sorted by the "timestamp" field (ISO-8601 string) when
        present.  The last session in sorted order is treated as the
        "current" session being evaluated; all earlier sessions are treated
        as prior history used for drift comparison.

        If timestamp is absent from all events, insertion order is used
        (i.e. the last unique session_id seen in the list is treated as
        current).  Callers without timestamps should therefore pass events
        in chronological order, oldest first.

    Example:
        history = [
            {"action_id": "a1", "agent_id": "agent_01", "session_id": "s1",
             "task_id": "t1", "operation": "READ", "resource": "tx_001",
             "policy_decision": "ALLOW"},
            {"action_id": "a2", "agent_id": "agent_01", "session_id": "s2",
             "task_id": "t1", "operation": "UPDATE", "resource": "tx_999",
             "policy_decision": "BLOCK"},
        ]
        score = compute_drift_score("agent_01", history)
        # score is an int, e.g. 45
    """
    # ------------------------------------------------------------------
    # Input validation — return 0 (not an exception) for bad inputs.
    # 0 does NOT confirm safe behaviour; it means the score is unknown.
    # ------------------------------------------------------------------
    if not isinstance(agent_id, str) or not agent_id.strip():
        return 0
    if not isinstance(history, list):
        return 0
    if len(history) == 0:
        return 0

    agent_id = agent_id.strip()

    # ------------------------------------------------------------------
    # Filter to this agent's actions only.
    # Actions for other agents are intentionally ignored.
    # ------------------------------------------------------------------
    agent_events = [
        e for e in history
        if isinstance(e, dict)
        and str(e.get("agent_id", "")).strip() == agent_id
    ]

    if not agent_events:
        return 0

    # ------------------------------------------------------------------
    # Sort by timestamp when the field is present so that session order
    # reflects chronological order rather than list insertion order.
    # This prevents a caller passing events out of time order from having
    # the wrong session treated as "current".
    #
    # Sorting rules:
    #   - Events with a non-empty timestamp string sort before events
    #     without one (unknown timestamps go to the end so they are
    #     treated as more-recent rather than silently discarded).
    #   - Within the same timestamp value, original list position is
    #     preserved (stable sort).
    # ------------------------------------------------------------------
    def _ts_key(e: dict) -> str:
        """Return sortable timestamp string; empty string sorts last."""
        ts = str(e.get("timestamp", "")).strip()
        # Events without timestamps are placed AFTER timestamped events.
        # We use a high sentinel so they sort as "most recent" when mixed,
        # which is the conservative direction.
        return ts if ts else "\xff"

    has_timestamps = any(str(e.get("timestamp", "")).strip() for e in agent_events)
    if has_timestamps:
        agent_events = sorted(agent_events, key=_ts_key)
    # If no timestamps at all, insertion order is used as-is.

    # ------------------------------------------------------------------
    # Load sorted events into a SessionHistory so the existing
    # scoring rules (cross-session repetition, baseline deviation)
    # can operate correctly.  Because events are now in chronological
    # order, the last session_id encountered is the most-recent one.
    # ------------------------------------------------------------------
    from drift.session_history import SessionHistory as _SH
    sh = _SH()
    sh.add_events(agent_events)

    # ------------------------------------------------------------------
    # Determine the most recent session (last in insertion order).
    # We score against the final session, treating everything before it
    # as prior history.  This gives the most conservative (highest)
    # signal when the agent's latest session is suspicious.
    # ------------------------------------------------------------------
    all_sessions = sh.get_all_sessions(agent_id)
    if not all_sessions:
        return 0

    latest_session_id = list(all_sessions.keys())[-1]
    latest_events = all_sessions[latest_session_id]

    # ------------------------------------------------------------------
    # Derive a synthetic policy result from the latest session's events.
    # If ANY event in the latest session was explicitly blocked, treat
    # the whole session as BLOCK for scoring purposes.
    # If no explicit policy_decision is present, treat as unverified.
    # ------------------------------------------------------------------
    decisions_in_latest = [
        str(e.get("policy_decision", "")).upper()
        for e in latest_events
    ]
    if "BLOCK" in decisions_in_latest:
        synthetic_policy = {"decision": "BLOCK"}
    elif "ALLOW" in decisions_in_latest:
        synthetic_policy = {"decision": "ALLOW"}
    else:
        synthetic_policy = {}   # unverified — scorer handles this safely

    # ------------------------------------------------------------------
    # Pick the most sensitive operation in the latest session as the
    # representative action.  More sensitive ops → higher scores, which
    # is the conservative and correct direction.
    # ------------------------------------------------------------------
    from drift.risk_score import SCORE_CONFIG as _SC
    _HIGH = _SC["high_risk_ops"]
    _MED  = _SC["medium_risk_ops"]

    def _op_rank(op: str) -> int:
        op = op.upper()
        if op in _HIGH:
            return 2
        if op in _MED:
            return 1
        return 0

    latest_ops = [
        str(e.get("operation", "")).strip()
        for e in latest_events
        if str(e.get("operation", "")).strip()
    ]
    if not latest_ops:
        return 0

    representative_op = max(latest_ops, key=_op_rank)

    # Build a minimal action dict using the shared schema fields.
    # Use the first available action_id from the latest session.
    first_event = next(
        (e for e in latest_events if e.get("action_id")),
        latest_events[0]
    )
    representative_action = {
        "action_id":  first_event.get("action_id", "compute_drift_synthetic"),
        "agent_id":   agent_id,
        "session_id": latest_session_id,
        "task_id":    first_event.get("task_id", ""),
        "operation":  representative_op,
        "resource":   first_event.get("resource", ""),
    }

    # ------------------------------------------------------------------
    # Score via the existing rule-based scorer and return only the int.
    # ------------------------------------------------------------------
    result = calculate_risk_score(representative_action, synthetic_policy, sh)
    return int(result.get("risk_score", 0))


# ---------------------------------------------------------------------------
# Quick demonstration — run: python -m drift.drift_assessor
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    history = build_demo_history()

    print("=" * 70)
    print("INTEGRATION INTERFACE DEMO — build_response() output")
    print("=" * 70)

    test_cases = [
        {
            "label": "Normal read (should be LOW risk, ALLOW)",
            "action": {
                "action_id": "act_demo_01",
                "agent_id": "agent_01",
                "session_id": "session_01",
                "task_id": "task_001",
                "operation": "READ",
                "resource": "transaction_TX1001",
            },
            "policy_result": {
                "decision": "ALLOW",
                "reason": "Operation is within the agent's authorized scope.",
            },
        },
        {
            "label": "Unauthorized write (should be HIGH/MEDIUM risk, BLOCK)",
            "action": {
                "action_id": "act_demo_02",
                "agent_id": "agent_01",
                "session_id": "session_07",
                "task_id": "task_001",
                "operation": "UPDATE",
                "resource": "transaction_TX9999",
            },
            "policy_result": {
                "decision": "BLOCK",
                "reason": "Write is outside the declared task scope.",
            },
        },
    ]

    for tc in test_cases:
        print(f"\n-- {tc['label']}")
        drift_result = assess_drift(
            action=tc["action"],
            policy_result=tc["policy_result"],
            session_history=history,
        )
        response = build_response(tc["action"], tc["policy_result"], drift_result)
        import json
        print(json.dumps(response, indent=2))
