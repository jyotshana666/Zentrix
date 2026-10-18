"""
tests/test_drift.py
===================
Tests for the Agent Warden-Z behavioral drift module.

Covers (matching the required test list from the implementation plan):
  1.  Empty history
  2.  One permitted read
  3.  Repeated permitted reads
  4.  One unauthorized write
  5.  Repeated unauthorized attempts
  6.  Export attempt
  7.  Deletion attempt
  8.  Unusual but permitted operation
  9.  Two different agents with independent histories
  10. Score boundaries and reproducibility
  11. Missing or malformed input
  12. A prohibited action that must remain prohibited regardless of risk score

Also covers SessionHistory unit tests.
"""

import pytest

from drift.session_history import SessionHistory
from drift.risk_score import calculate_risk_score, SCORE_CONFIG
from drift.drift_assessor import assess_drift, build_response


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def make_action(
    action_id="act_test",
    agent_id="agent_test",
    session_id="session_test",
    task_id="task_test",
    operation="READ",
    resource="transaction_TX0001",
):
    """Build a minimal valid action dict."""
    return {
        "action_id": action_id,
        "agent_id": agent_id,
        "session_id": session_id,
        "task_id": task_id,
        "operation": operation,
        "resource": resource,
    }


def allow():
    return {"decision": "ALLOW"}


def block():
    return {"decision": "BLOCK"}


def hold():
    return {"decision": "HOLD"}


# ---------------------------------------------------------------------------
# SessionHistory unit tests
# ---------------------------------------------------------------------------

class TestSessionHistory:

    def test_empty_history_returns_empty_sessions(self):
        """Test 1: Empty history — no crash, returns empty structures."""
        h = SessionHistory()
        assert h.get_all_sessions("agent_x") == {}
        assert h.get_session("agent_x", "session_x") == []
        assert h.get_past_sessions("agent_x", "session_x") == {}
        assert h.known_agents() == []
        assert h.session_count("agent_x") == 0
        assert h.event_count("agent_x") == 0

    def test_add_valid_event(self):
        h = SessionHistory()
        event = make_action()
        ok, msg = h.add_event(event)
        assert ok is True
        assert msg == "OK"

    def test_events_grouped_by_session(self):
        h = SessionHistory()
        h.add_event(make_action(action_id="a1", session_id="s1"))
        h.add_event(make_action(action_id="a2", session_id="s1"))
        h.add_event(make_action(action_id="a3", session_id="s2"))
        sessions = h.get_all_sessions("agent_test")
        assert "s1" in sessions
        assert "s2" in sessions
        assert len(sessions["s1"]) == 2
        assert len(sessions["s2"]) == 1

    def test_agents_are_isolated(self):
        """Test 9 (partial): Different agents must not share history."""
        h = SessionHistory()
        h.add_event(make_action(agent_id="agent_A", session_id="s1"))
        h.add_event(make_action(agent_id="agent_B", session_id="s2"))
        assert h.event_count("agent_A") == 1
        assert h.event_count("agent_B") == 1
        assert h.get_session("agent_A", "s2") == []
        assert h.get_session("agent_B", "s1") == []

    def test_past_sessions_stops_at_current(self):
        h = SessionHistory()
        h.add_event(make_action(session_id="s1"))
        h.add_event(make_action(session_id="s2"))
        h.add_event(make_action(session_id="s3"))
        past = h.get_past_sessions("agent_test", before_session_id="s3")
        assert "s1" in past
        assert "s2" in past
        assert "s3" not in past

    def test_malformed_event_rejected(self):
        """Test 11 (partial): Malformed events must not crash the system."""
        h = SessionHistory()
        ok, msg = h.add_event("not a dict")
        assert ok is False
        assert "dict" in msg.lower()

    def test_missing_required_field_rejected(self):
        h = SessionHistory()
        bad = {"agent_id": "agent_x"}  # missing other required fields
        ok, msg = h.add_event(bad)
        assert ok is False
        assert "missing" in msg.lower()

    def test_empty_agent_id_rejected(self):
        h = SessionHistory()
        event = make_action()
        event["agent_id"] = ""
        ok, msg = h.add_event(event)
        assert ok is False

    def test_event_count(self):
        h = SessionHistory()
        h.add_event(make_action(action_id="a1", session_id="s1"))
        h.add_event(make_action(action_id="a2", session_id="s1"))
        assert h.event_count("agent_test", "s1") == 2
        assert h.event_count("agent_test") == 2


# ---------------------------------------------------------------------------
# Risk score tests
# ---------------------------------------------------------------------------

class TestRiskScore:

    # ---- Test 1: Empty history ----

    def test_empty_history_no_crash(self):
        """Test 1: Empty history must not crash the scorer."""
        action = make_action(operation="READ")
        result = calculate_risk_score(action, allow(), None)
        assert isinstance(result, dict)
        assert "risk_score" in result
        assert 0 <= result["risk_score"] <= 100

    # ---- Test 2: One permitted read ----

    def test_single_permitted_read_is_low(self):
        """Test 2: A single permitted READ should produce a LOW risk score."""
        action = make_action(operation="READ")
        result = calculate_risk_score(action, allow(), None)
        assert result["risk_score"] == 0
        assert result["risk_level"] == "LOW"

    # ---- Test 3: Repeated permitted reads ----

    def test_repeated_permitted_reads_remain_low(self):
        """Test 3: Multiple permitted reads must stay LOW risk."""
        h = SessionHistory()
        for i in range(5):
            h.add_event(make_action(
                action_id=f"a{i}",
                session_id="s1",
                operation="READ",
            ))
        action = make_action(session_id="s2", operation="READ")
        result = calculate_risk_score(action, allow(), h)
        assert result["risk_level"] == "LOW"

    # ---- Test 4: One unauthorized write ----

    def test_one_unauthorized_write_raises_score(self):
        """Test 4: One blocked UPDATE should score above 0."""
        action = make_action(operation="UPDATE")
        result = calculate_risk_score(action, block(), None)
        assert result["risk_score"] > 0
        assert result["risk_level"] in ("MEDIUM", "HIGH")

    def test_policy_block_is_present_in_reasons(self):
        action = make_action(operation="UPDATE")
        result = calculate_risk_score(action, block(), None)
        reasons_text = " ".join(result["reasons"])
        assert "BLOCK" in reasons_text or "blocked" in reasons_text.lower()

    # ---- Test 5: Repeated unauthorized attempts ----

    def test_repeated_unauthorized_raises_score_further(self):
        """Test 5: Repeated blocks across sessions must increase the risk score."""
        h = SessionHistory()
        # Add two prior sessions that were both blocked
        h.add_event(
            make_action(action_id="prior1", session_id="s1", operation="UPDATE")
            | {"policy_decision": "BLOCK"}
        )
        h.add_event(
            make_action(action_id="prior2", session_id="s2", operation="UPDATE")
            | {"policy_decision": "BLOCK"}
        )

        action = make_action(session_id="s3", operation="UPDATE")
        result_with_history = calculate_risk_score(action, block(), h)

        result_no_history = calculate_risk_score(action, block(), None)

        assert result_with_history["risk_score"] >= result_no_history["risk_score"], (
            "Repeated unauthorized attempts must not lower the risk score."
        )

    def test_escalation_reason_present(self):
        """Prior blocked sessions must appear in the reasons."""
        h = SessionHistory()
        h.add_event(make_action(
            action_id="p1", session_id="s1",
            operation="UPDATE",
        ) | {"policy_decision": "BLOCK"})

        action = make_action(session_id="s2", operation="UPDATE")
        result = calculate_risk_score(action, block(), h)
        reasons = " ".join(result["reasons"]).lower()
        assert "prior" in reasons or "escalat" in reasons or "session" in reasons

    # ---- Test 6: Export attempt ----

    def test_export_is_high_risk(self):
        """Test 6: EXPORT must trigger the high-risk operation penalty."""
        action = make_action(operation="EXPORT")
        result = calculate_risk_score(action, block(), None)
        assert result["risk_score"] >= (
            SCORE_CONFIG["policy_block_weight"] + SCORE_CONFIG["high_risk_op_weight"]
        )

    # ---- Test 7: Delete attempt ----

    def test_delete_is_high_risk(self):
        """Test 7: DELETE must trigger the high-risk operation penalty."""
        action = make_action(operation="DELETE")
        result = calculate_risk_score(action, block(), None)
        assert result["risk_score"] >= (
            SCORE_CONFIG["policy_block_weight"] + SCORE_CONFIG["high_risk_op_weight"]
        )

    # ---- Test 8: Unusual but permitted operation ----

    def test_unusual_but_permitted_is_not_a_violation(self):
        """
        Test 8: An unusual-but-permitted operation (ALLOW decision, uncommon op)
        must NOT be treated as a policy violation.
        """
        action = make_action(operation="SUMMARIZE")
        result = calculate_risk_score(action, allow(), None)
        # Must not receive the policy_block_weight
        assert result["risk_score"] < SCORE_CONFIG["policy_block_weight"], (
            "An ALLOW decision must not apply the policy-block penalty."
        )
        # The ALLOW decision must be visible in the reasons
        reasons_text = " ".join(result["reasons"]).lower()
        assert "allow" in reasons_text

    # ---- Test 9: Two different agents with independent histories ----

    def test_two_agents_independent(self):
        """Test 9: agent_A's blocks must not affect agent_B's risk score."""
        h = SessionHistory()

        # agent_A has many prior blocks
        for i in range(3):
            h.add_event(make_action(
                action_id=f"a_block_{i}",
                agent_id="agent_A",
                session_id=f"sA_{i}",
                operation="UPDATE",
            ) | {"policy_decision": "BLOCK"})

        # agent_B is clean
        action_b = make_action(
            agent_id="agent_B",
            session_id="sB_1",
            operation="READ",
        )
        result_b = calculate_risk_score(action_b, allow(), h)

        # agent_B should score 0 — their own history is clean
        assert result_b["risk_score"] == 0, (
            f"agent_B should have risk_score=0 but got {result_b['risk_score']}. "
            "agent_A's history must not bleed into agent_B's score."
        )

    # ---- Test 10: Score boundaries and reproducibility ----

    def test_score_bounded_low(self):
        """Test 10a: Score must never go below 0."""
        action = make_action(operation="READ")
        result = calculate_risk_score(action, allow(), None)
        assert result["risk_score"] >= 0

    def test_score_bounded_high(self):
        """Test 10b: Score must never exceed 100."""
        h = SessionHistory()
        # Load many prior blocked sessions
        for i in range(20):
            h.add_event(make_action(
                action_id=f"block_{i}",
                session_id=f"s{i}",
                operation="DELETE",
            ) | {"policy_decision": "BLOCK"})
        action = make_action(session_id="s_current", operation="DELETE")
        result = calculate_risk_score(action, block(), h)
        assert result["risk_score"] <= 100, (
            f"Score exceeded 100: {result['risk_score']}"
        )

    def test_score_is_deterministic(self):
        """Test 10c: Same input must always produce same output."""
        h = SessionHistory()
        h.add_event(make_action(
            action_id="p1", session_id="s1", operation="READ",
        ) | {"policy_decision": "ALLOW"})

        action = make_action(session_id="s2", operation="UPDATE")
        r1 = calculate_risk_score(action, block(), h)
        r2 = calculate_risk_score(action, block(), h)
        assert r1["risk_score"] == r2["risk_score"], "Scorer must be deterministic."
        assert r1["reasons"] == r2["reasons"]

    # ---- Test 11: Missing or malformed input ----

    def test_none_action_returns_error_result(self):
        """Test 11a: None action must not crash — returns error dict."""
        result = calculate_risk_score(None, allow(), None)
        assert "risk_score" in result
        assert 0 <= result["risk_score"] <= 100
        assert result["agent_id"] == "unknown"

    def test_missing_agent_id_returns_error(self):
        """Test 11b: Missing agent_id must return a safe error result."""
        action = make_action()
        action["agent_id"] = ""
        result = calculate_risk_score(action, allow(), None)
        assert result["agent_id"] == "unknown"
        assert "INPUT ERROR" in result["reasons"][0]

    def test_missing_operation_returns_error(self):
        """Test 11c: Missing operation must return a safe error result."""
        action = make_action()
        action["operation"] = ""
        result = calculate_risk_score(action, allow(), None)
        assert result["agent_id"] == "unknown"

    def test_none_policy_result_handled(self):
        """Test 11d: None policy result must not crash."""
        action = make_action(operation="READ")
        result = calculate_risk_score(action, None, None)
        assert "risk_score" in result
        assert 0 <= result["risk_score"] <= 100

    def test_empty_policy_result_handled(self):
        """Test 11e: Empty policy result dict must not crash."""
        action = make_action(operation="READ")
        result = calculate_risk_score(action, {}, None)
        assert "risk_score" in result

    # ---- Test 12: Prohibited action remains prohibited ----

    def test_blocked_action_never_becomes_allow_due_to_low_score(self):
        """
        Test 12: A BLOCK decision must remain visible regardless of risk score.
        The drift module must NOT convert BLOCK to ALLOW.
        """
        action = make_action(operation="READ")
        # Even a "harmless" READ can be blocked by policy
        policy = {"decision": "BLOCK", "reason": "Agent not authorized for this resource."}
        drift = assess_drift(action, policy, None)
        response = build_response(action, policy, drift)

        assert response["decision"] == "BLOCK", (
            "A policy BLOCK must remain BLOCK — the drift module must not override it."
        )
        assert response["executed"] is False, (
            "executed must always be False — drift module never executes DB operations."
        )


# ---------------------------------------------------------------------------
# Integration interface tests
# ---------------------------------------------------------------------------

class TestDriftAssessor:

    def test_assess_drift_returns_required_fields(self):
        action = make_action(operation="READ")
        result = assess_drift(action, allow(), None)
        required = {"agent_id", "session_id", "action_id", "risk_score",
                    "risk_level", "reasons"}
        assert required.issubset(result.keys()), (
            f"assess_drift() is missing fields: {required - result.keys()}"
        )

    def test_build_response_includes_shared_schema_fields(self):
        action = make_action()
        drift = assess_drift(action, allow(), None)
        response = build_response(action, allow(), drift)

        # Shared schema required fields
        assert "action_id" in response
        assert "decision" in response
        assert "reason" in response
        assert "risk_score" in response
        assert "executed" in response

    def test_build_response_executed_always_false(self):
        action = make_action(operation="DELETE")
        drift = assess_drift(action, block(), None)
        response = build_response(action, block(), drift)
        assert response["executed"] is False

    def test_assess_drift_with_history(self):
        """Full integration: assess drift using populated session history."""
        h = SessionHistory()
        h.add_event(make_action(
            action_id="hist_1", session_id="s1",
            operation="UPDATE",
        ) | {"policy_decision": "BLOCK"})

        action = make_action(session_id="s2", operation="UPDATE")
        result = assess_drift(action, block(), h)
        assert result["risk_score"] > 0
        assert result["risk_level"] in ("MEDIUM", "HIGH")

    def test_risk_level_bands(self):
        """Verify the risk level bands LOW/MEDIUM/HIGH are assigned correctly."""
        from drift.risk_score import _risk_level
        assert _risk_level(0) == "LOW"
        assert _risk_level(SCORE_CONFIG["low_max"]) == "LOW"
        assert _risk_level(SCORE_CONFIG["low_max"] + 1) == "MEDIUM"
        assert _risk_level(SCORE_CONFIG["medium_max"]) == "MEDIUM"
        assert _risk_level(SCORE_CONFIG["medium_max"] + 1) == "HIGH"
        assert _risk_level(100) == "HIGH"


# ---------------------------------------------------------------------------
# Tests for compute_drift_score() — the teammate-facing function
# ---------------------------------------------------------------------------
# Import path for the policy engine teammate:
#   from drift.drift_assessor import compute_drift_score
# ---------------------------------------------------------------------------

from drift.drift_assessor import compute_drift_score


def _event(
    agent_id="agent_cds",
    session_id="s1",
    action_id=None,
    operation="READ",
    resource="tx_001",
    task_id="task_cds",
    policy_decision=None,
):
    """Build a minimal action dict for compute_drift_score tests."""
    e = {
        "action_id":  action_id or f"act_{agent_id}_{session_id}_{operation}",
        "agent_id":   agent_id,
        "session_id": session_id,
        "task_id":    task_id,
        "operation":  operation,
        "resource":   resource,
    }
    if policy_decision is not None:
        e["policy_decision"] = policy_decision
    return e


class TestComputeDriftScore:
    """
    Tests for compute_drift_score(agent_id, history) -> int.

    Function contract:
      - Accepts an agent_id str and a list[dict] of action records.
      - Returns an int in [0, 100].
      - Only the specified agent's records are scored.
      - Deterministic: same input => same int output.
    """

    # ---- 1. Empty history ----

    def test_empty_list_returns_zero(self):
        """Empty history must return 0 without crashing."""
        score = compute_drift_score("agent_cds", [])
        assert score == 0
        assert isinstance(score, int)

    def test_empty_string_agent_id_returns_zero(self):
        """Invalid agent_id must not crash; returns 0."""
        history = [_event()]
        assert compute_drift_score("", history) == 0

    def test_none_agent_id_returns_zero(self):
        assert compute_drift_score(None, []) == 0

    def test_non_list_history_returns_zero(self):
        """Non-list history must not raise; returns 0."""
        assert compute_drift_score("agent_cds", None) == 0
        assert compute_drift_score("agent_cds", {}) == 0

    # ---- 2. Normal permitted reads ----

    def test_single_permitted_read_is_zero(self):
        """One ALLOW READ should score 0."""
        history = [_event(operation="READ", policy_decision="ALLOW")]
        score = compute_drift_score("agent_cds", history)
        assert score == 0
        assert isinstance(score, int)

    def test_multiple_permitted_reads_stay_low(self):
        """Multiple ALLOW READs across sessions should stay LOW."""
        history = [
            _event(session_id="s1", operation="READ", policy_decision="ALLOW"),
            _event(session_id="s1", action_id="a2", operation="READ", policy_decision="ALLOW"),
            _event(session_id="s2", action_id="a3", operation="READ", policy_decision="ALLOW"),
        ]
        score = compute_drift_score("agent_cds", history)
        assert score < SCORE_CONFIG["low_max"] + 1, (
            f"Repeated permitted reads should be LOW, got {score}"
        )

    # ---- 3. One unauthorized action ----

    def test_single_blocked_update_raises_score(self):
        """One BLOCK on an UPDATE should produce a score > 0."""
        history = [_event(operation="UPDATE", policy_decision="BLOCK")]
        score = compute_drift_score("agent_cds", history)
        assert score > 0, f"One unauthorized UPDATE should score > 0, got {score}"
        assert isinstance(score, int)

    def test_single_blocked_delete_raises_score(self):
        """One blocked DELETE should score higher than a blocked UPDATE."""
        history_update = [_event(operation="UPDATE", policy_decision="BLOCK")]
        history_delete = [_event(operation="DELETE", policy_decision="BLOCK")]
        score_update = compute_drift_score("agent_cds", history_update)
        score_delete = compute_drift_score("agent_cds", history_delete)
        assert score_delete >= score_update, (
            f"DELETE ({score_delete}) should score >= UPDATE ({score_update})"
        )

    def test_single_blocked_export_raises_score(self):
        """One blocked EXPORT should produce a score above 0."""
        history = [_event(operation="EXPORT", policy_decision="BLOCK")]
        score = compute_drift_score("agent_cds", history)
        assert score > 0

    # ---- 4. Repeated unauthorized actions across sessions ----

    def test_repeated_blocks_increase_score(self):
        """Repeated BLOCK events across multiple sessions should score higher."""
        history_one = [
            _event(session_id="s1", operation="UPDATE", policy_decision="ALLOW"),
            _event(session_id="s2", action_id="a2", operation="UPDATE",
                   policy_decision="BLOCK"),
        ]
        history_repeated = [
            _event(session_id="s1", operation="UPDATE", policy_decision="BLOCK"),
            _event(session_id="s2", action_id="a2", operation="UPDATE",
                   policy_decision="BLOCK"),
            _event(session_id="s3", action_id="a3", operation="UPDATE",
                   policy_decision="BLOCK"),
        ]
        score_one      = compute_drift_score("agent_cds", history_one)
        score_repeated = compute_drift_score("agent_cds", history_repeated)
        assert score_repeated >= score_one, (
            f"Repeated blocks ({score_repeated}) must not score lower "
            f"than a single block ({score_one})."
        )

    # ---- 5. Multiple agents in the same history list ----

    def test_only_target_agent_is_scored(self):
        """
        If the history list contains events from two agents, only the
        requested agent's events must affect the score.
        """
        history = [
            # agent_A has many suspicious blocks
            _event(agent_id="agent_A", session_id="sA1",
                   operation="DELETE", policy_decision="BLOCK"),
            _event(agent_id="agent_A", session_id="sA2",
                   action_id="aA2", operation="EXPORT", policy_decision="BLOCK"),
            # agent_B is completely clean
            _event(agent_id="agent_B", session_id="sB1",
                   operation="READ", policy_decision="ALLOW"),
        ]
        score_b = compute_drift_score("agent_B", history)
        assert score_b == 0, (
            f"agent_B should score 0 (only permitted READs), got {score_b}. "
            "agent_A's BLOCK history must not contaminate agent_B's score."
        )

    def test_unknown_agent_scores_zero(self):
        """An agent not present in the history must score 0."""
        history = [_event(agent_id="agent_A", operation="READ")]
        score = compute_drift_score("agent_Z", history)
        assert score == 0

    # ---- 6. Unusual but permitted actions ----

    def test_unusual_permitted_op_does_not_score_as_violation(self):
        """
        An operation like SUMMARIZE that is ALLOW (unusual but not prohibited)
        must not score as high as a BLOCK.
        """
        history_unusual = [_event(operation="SUMMARIZE", policy_decision="ALLOW")]
        history_blocked  = [_event(operation="UPDATE",    policy_decision="BLOCK")]
        score_unusual = compute_drift_score("agent_cds", history_unusual)
        score_blocked  = compute_drift_score("agent_cds", history_blocked)
        assert score_unusual < score_blocked, (
            f"Unusual-but-permitted SUMMARIZE ({score_unusual}) must score "
            f"lower than a blocked UPDATE ({score_blocked})."
        )

    # ---- 7. Score lower and upper bounds ----

    def test_score_never_below_zero(self):
        score = compute_drift_score("agent_cds", [])
        assert score >= 0

    def test_score_never_above_100(self):
        """Even with many prior blocks the score must not exceed 100."""
        history = [
            _event(
                agent_id="agent_cds",
                session_id=f"s{i}",
                action_id=f"act_{i}",
                operation="DELETE",
                policy_decision="BLOCK",
            )
            for i in range(30)
        ]
        score = compute_drift_score("agent_cds", history)
        assert score <= 100, f"Score must never exceed 100, got {score}"

    # ---- 8. Deterministic results ----

    def test_same_input_same_output(self):
        """Calling compute_drift_score twice with identical input must return the same int."""
        history = [
            _event(session_id="s1", operation="READ",   policy_decision="ALLOW"),
            _event(session_id="s2", action_id="a2",
                   operation="UPDATE", policy_decision="BLOCK"),
        ]
        score1 = compute_drift_score("agent_cds", history)
        score2 = compute_drift_score("agent_cds", history)
        assert score1 == score2, (
            f"compute_drift_score is not deterministic: got {score1} then {score2}"
        )

    # ---- 9. Correct integer return type ----

    def test_return_type_is_int_for_empty(self):
        assert type(compute_drift_score("x", [])) is int

    def test_return_type_is_int_for_normal(self):
        history = [_event(operation="READ", policy_decision="ALLOW")]
        assert type(compute_drift_score("agent_cds", history)) is int

    def test_return_type_is_int_for_suspicious(self):
        history = [_event(operation="DELETE", policy_decision="BLOCK")]
        assert type(compute_drift_score("agent_cds", history)) is int

    # ---- Integration concern: BLOCK decision is never softened by this function ----

    def test_function_does_not_return_decision(self):
        """
        compute_drift_score() returns only an int.
        It must NOT return a dict, decision string, or policy object.
        The policy engine (apply_drift) handles all decision changes.
        """
        history = [_event(operation="UPDATE", policy_decision="BLOCK")]
        result = compute_drift_score("agent_cds", history)
        assert isinstance(result, int), (
            "compute_drift_score must return only an int, not a dict or string."
        )

    # ---- Session ordering: timestamp vs insertion order ----

    def test_timestamp_ordering_overrides_insertion_order(self):
        """
        When timestamp is present, events are sorted chronologically so the
        LATEST session by time is always treated as current — regardless of
        list insertion order.

        Scenario: s2 (blocked UPDATE, timestamp=later) is the current session.
                  s1 (safe READ, timestamp=earlier) is prior history.
        The history list is passed with s2 FIRST (wrong insertion order).
        The score must still reflect s2 as current, not s1.
        """
        history_reversed = [
            # Chronologically LATER session passed first in the list
            {
                "action_id": "a2", "agent_id": "agent_cds", "session_id": "s2",
                "task_id": "t", "operation": "UPDATE", "resource": "r",
                "policy_decision": "BLOCK",
                "timestamp": "2026-01-12T10:00:00+00:00",  # later
            },
            # Chronologically EARLIER session passed second in the list
            {
                "action_id": "a1", "agent_id": "agent_cds", "session_id": "s1",
                "task_id": "t", "operation": "READ", "resource": "r",
                "policy_decision": "ALLOW",
                "timestamp": "2026-01-11T10:00:00+00:00",  # earlier
            },
        ]
        score = compute_drift_score("agent_cds", history_reversed)
        # s2 (BLOCK + UPDATE) is the latest by timestamp, so the score must
        # reflect the block penalty, not a clean-read result.
        assert score > 0, (
            f"Expected score > 0 when the chronologically-latest session has a "
            f"BLOCK+UPDATE, but got {score}. "
            "Timestamp sorting may not be working."
        )

    def test_no_timestamps_uses_insertion_order(self):
        """
        When no timestamps are present, insertion order is the tie-breaker.
        The last session_id appearing in the list is treated as current.
        Callers without timestamps must pass events oldest-first.
        """
        history = [
            # s1 first = older (prior history)
            {
                "action_id": "a1", "agent_id": "agent_cds", "session_id": "s1",
                "task_id": "t", "operation": "READ", "resource": "r",
                "policy_decision": "ALLOW",
            },
            # s2 last = newest (current session)
            {
                "action_id": "a2", "agent_id": "agent_cds", "session_id": "s2",
                "task_id": "t", "operation": "UPDATE", "resource": "r",
                "policy_decision": "BLOCK",
            },
        ]
        score = compute_drift_score("agent_cds", history)
        assert score > 0, (
            f"Expected score > 0 (s2 is BLOCK+UPDATE, treated as current), got {score}."
        )
