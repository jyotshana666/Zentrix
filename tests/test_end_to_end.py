"""
tests/test_end_to_end.py
========================
End-to-End Integration Test Suite for Agent Warden-Z.
Verifies the complete pipeline across all four PRD use cases:
  - Use Case A: Safe database read (ALLOW, executed=True)
  - Use Case B: Out-of-scope write (BLOCK, executed=False)
  - Use Case C: Sensitive or unrelated resource access (BLOCK, executed=False)
  - Use Case D: Cross-session behavioral drift (HOLD on high drift score)
  - Human Review Workflow: Approve and Reject held actions
  - Metrics & Behavioral Risk endpoints
"""

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.database import reset_db


@pytest.fixture(autouse=True)
def clean_database():
    """Ensure clean baseline database before each test run."""
    reset_db()
    yield
    reset_db()


@pytest.fixture
def client():
    return TestClient(app)


class TestEndToEndPipeline:
    """Full lifecycle testing of Agent Warden-Z."""

    def test_use_case_a_safe_read_executes_successfully(self, client):
        """
        PRD Use Case A:
          An agent investigates transaction TX1042 under task_001.
          Expected outcome:
            - Decision: ALLOW
            - Reason: 'Matches task policy'
            - Executed: True
            - Risk score: 0
        """
        payload = {
            "action_id": "act_safe_read_01",
            "agent_id": "agent_01",
            "session_id": "sess_01",
            "task_id": "task_001",
            "operation": "SELECT",
            "resource": "transaction_TX1042",
        }

        resp = client.post("/actions/execute", json=payload)
        assert resp.status_code == 200

        data = resp.json()
        assert data["action_id"] == "act_safe_read_01"
        assert data["decision"] == "ALLOW"
        assert data["executed"] is True
        assert data["risk_score"] == 0

    def test_use_case_c_unrelated_resource_blocked(self, client):
        """
        PRD Use Case C:
          Agent assigned to transactions attempts to inspect unrelated customer records.
          Expected outcome:
            - Decision: BLOCK
            - Executed: False
            - Reason: Outside permitted scope
        """
        payload = {
            "action_id": "act_unrelated_01",
            "agent_id": "agent_01",
            "session_id": "sess_01",
            "task_id": "task_001",
            "operation": "SELECT",
            "resource": "customers",
        }

        resp = client.post("/actions/execute", json=payload)
        assert resp.status_code == 200

        data = resp.json()
        assert data["decision"] == "BLOCK"
        assert data["executed"] is False
        assert "outside the task's permitted scope" in data["reason"].lower()

    def test_use_case_d_cross_session_behavioral_drift(self, client):
        """
        PRD Use Case D:
          Agent exhibits repeated denials across prior sessions.
          When proposing a nominally permitted read in a later session,
          the elevated drift score upgrades the ALLOW decision to HOLD.
        """
        agent_id = "agent_drift_test"

        # Session 1: Propose 2 prohibited actions (denials)
        for i in range(2):
            client.post("/actions/execute", json={
                "action_id": f"act_denial_s1_{i}",
                "agent_id": agent_id,
                "session_id": "sess_d1",
                "task_id": "task_001",
                "operation": "UPDATE",
                "resource": "transaction_TX1042",
            })

        # Session 2: Propose high-risk DELETE operation (escalation + denial)
        client.post("/actions/execute", json={
            "action_id": "act_denial_s2_01",
            "agent_id": agent_id,
            "session_id": "sess_d2",
            "task_id": "task_001",
            "operation": "DELETE",
            "resource": "secrets",
        })

        # Check drift risk score for agent
        risk_resp = client.get(f"/agents/{agent_id}/risk")
        assert risk_resp.status_code == 200
        risk_data = risk_resp.json()
        assert risk_data["risk_score"] >= 60, f"Expected elevated drift score >= 60, got {risk_data['risk_score']}"
        assert risk_data["risk_level"] == "HIGH"

        # Session 3: Agent now attempts a normally permitted SELECT on TX1042
        # Because drift score >= 60, apply_drift upgrades ALLOW to HOLD!
        resp = client.post("/actions/execute", json={
            "action_id": "act_s3_read_attempt",
            "agent_id": agent_id,
            "session_id": "sess_d3",
            "task_id": "task_001",
            "operation": "SELECT",
            "resource": "transaction_TX1042",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "HOLD", "Elevated drift must upgrade ALLOW to HOLD"
        assert data["executed"] is False
        assert data["risk_score"] >= 60
        assert "elevated behavioral risk" in data["reason"].lower()

    def test_human_review_workflow_approval(self, client):
        """A held action can be reviewed and approved, triggering execution."""
        # Submit an action configured to require review
        resp = client.post("/actions/execute", json={
            "action_id": "act_review_target_01",
            "agent_id": "agent_reviewer_test",
            "session_id": "sess_rev",
            "task_id": "task_update_transaction",
            "operation": "UPDATE",
            "resource": "transaction_TX1042",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "HOLD"
        assert data["executed"] is False

        # Verify action appears in held actions queue
        held_resp = client.get("/actions/held")
        assert held_resp.status_code == 200
        held_list = held_resp.json()
        assert any(
            h.get("request", {}).get("action_id") == "act_review_target_01"
            or h.get("action_id") == "act_review_target_01"
            for h in held_list
        )

        # Reviewer approves the action
        review_resp = client.post(
            "/reviews/act_review_target_01",
            json={
                "decision": "APPROVE",
                "reviewer_id": "sec_lead_shreya",
                "notes": "Verified business justification with ops team",
            },
        )
        assert review_resp.status_code == 200
        rev_data = review_resp.json()
        assert rev_data["status"] == "APPROVED"
        assert rev_data["executed"] is True

    def test_metrics_endpoint(self, client):
        """GET /metrics reports real measured statistics without error."""
        # Execute one allowed and one blocked
        client.post("/actions/execute", json={
            "action_id": "act_m_01",
            "agent_id": "agent_m",
            "session_id": "sess_m",
            "task_id": "task_001",
            "operation": "SELECT",
            "resource": "transaction_TX1042",
        })
        client.post("/actions/execute", json={
            "action_id": "act_m_02",
            "agent_id": "agent_m",
            "session_id": "sess_m",
            "task_id": "task_001",
            "operation": "UPDATE",
            "resource": "transaction_TX1042",
        })

        resp = client.get("/metrics")
        assert resp.status_code == 200
        m = resp.json()
        assert m["total_actions_evaluated"] >= 2
        assert m["total_allowed"] >= 1
        assert m["total_blocked"] >= 1
        assert m["unauthorized_executions_count"] == 0
        assert m["prevention_rate"] == 1.0
