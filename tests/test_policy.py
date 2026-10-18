import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.policy_engine import (
    TASK_POLICIES,
    apply_drift,
    evaluate_action,
    get_task_policy,
    list_task_policies,
    register_task_policy,
)
from backend.schemas import (
    ActionRequest,
    DecisionResponse,
    EvaluateResponse,
    TaskRegistrationRequest,
)


@pytest.fixture
def client():
    return TestClient(app)


class TestSchemaNormalization:
    """Test schema validation and normalization for operations and resources."""

    def test_operation_read_normalizes_to_select(self):
        req = ActionRequest(
            action_id="act_test_01",
            agent_id="agent_01",
            session_id="session_01",
            task_id="task_001",
            operation="read",
            resource="transaction_TX1042",
        )
        assert req.operation == "SELECT"

    def test_operation_write_normalizes_to_update(self):
        req = ActionRequest(
            action_id="act_test_02",
            agent_id="agent_01",
            session_id="session_01",
            task_id="task_001",
            operation="write",
            resource="transaction_TX1042",
        )
        assert req.operation == "UPDATE"

    def test_arbitrary_operations_allowed_and_uppercased(self):
        req = ActionRequest(
            action_id="act_test_03",
            agent_id="agent_01",
            session_id="session_01",
            task_id="task_001",
            operation=" export ",
            resource="transaction_TX1042",
        )
        assert req.operation == "EXPORT"


class TestPolicyEvaluation:
    """Test deterministic policy evaluation for core demo use cases."""

    def test_use_case_a_safe_read_allowed(self):
        """PRD Use Case A: Authorized read on permitted transaction TX1042 is ALLOWED."""
        req = ActionRequest(
            action_id="act_001",
            agent_id="agent_01",
            session_id="session_01",
            task_id="task_read_transaction",
            operation="SELECT",
            resource="transaction_TX1042",
        )
        res = evaluate_action(req)
        assert res.decision == "ALLOW"
        assert res.risk_score == 0
        assert "Matches task policy" in res.reason
        assert res.executed is False  # Policy engine never sets executed=True directly

    def test_use_case_a_synonym_read_allowed_on_task_001(self):
        """PRD Demo Task 001: READ is normalized to SELECT and allowed on TX1042."""
        req = ActionRequest(
            action_id="act_001_b",
            agent_id="agent_01",
            session_id="session_01",
            task_id="task_001",
            operation="READ",
            resource="transaction_TX1042",
        )
        res = evaluate_action(req)
        assert res.decision == "ALLOW"
        assert res.risk_score == 0

    def test_use_case_b_out_of_scope_write_blocked(self):
        """PRD Use Case B: UPDATE during a read-only task is strictly BLOCKED."""
        req = ActionRequest(
            action_id="act_002",
            agent_id="agent_01",
            session_id="session_01",
            task_id="task_read_transaction",
            operation="UPDATE",
            resource="transaction_TX1042",
        )
        res = evaluate_action(req)
        assert res.decision == "BLOCK"
        assert res.risk_score == 100
        assert "not permitted by the task policy" in res.reason
        assert res.executed is False

    def test_use_case_b_out_of_scope_write_on_task_001_blocked(self):
        """PRD Use Case B: UPDATE on task_001 is BLOCKED."""
        req = ActionRequest(
            action_id="act_002_b",
            agent_id="agent_01",
            session_id="session_01",
            task_id="task_001",
            operation="UPDATE",
            resource="transaction_TX1042",
        )
        res = evaluate_action(req)
        assert res.decision == "BLOCK"
        assert res.risk_score == 100

    def test_use_case_c_unrelated_resource_blocked(self):
        """PRD Use Case C: Attempting to access customer records under transaction task is BLOCKED."""
        req = ActionRequest(
            action_id="act_003",
            agent_id="agent_01",
            session_id="session_01",
            task_id="task_read_transaction",
            operation="SELECT",
            resource="customer_CUST001",
        )
        res = evaluate_action(req)
        assert res.decision == "BLOCK"
        assert res.risk_score == 100
        assert "outside the task's permitted scope" in res.reason

    def test_sensitive_operation_review_hold(self):
        """PRD FR-12: Sensitive operations marked for review return HOLD."""
        req = ActionRequest(
            action_id="act_004",
            agent_id="agent_01",
            session_id="session_01",
            task_id="task_update_transaction",
            operation="UPDATE",
            resource="transactions",
        )
        res = evaluate_action(req)
        assert res.decision == "HOLD"
        assert res.risk_score == 60
        assert "Additional authorization required" in res.reason

    def test_unknown_task_fails_closed(self):
        """Unknown tasks must be BLOCKED with risk 100."""
        req = ActionRequest(
            action_id="act_005",
            agent_id="agent_01",
            session_id="session_01",
            task_id="non_existent_task",
            operation="SELECT",
            resource="transactions",
        )
        res = evaluate_action(req)
        assert res.decision == "BLOCK"
        assert res.risk_score == 100
        assert "Unknown task" in res.reason


class TestDynamicTaskRegistry:
    """Test dynamic task registration and intent declaration."""

    def test_register_and_evaluate_dynamic_task(self):
        task_def = TaskRegistrationRequest(
            task_id="task_audit_2026",
            agent_id="agent_audit",
            purpose="Annual security audit",
            allowed_operations=["SELECT"],
            allowed_resources=["audit_log", "transactions"],
            requires_review_for=["EXPORT"],
        )
        registered = register_task_policy(task_def)
        assert registered["allowed_operations"] == ["SELECT"]
        assert "audit_log" in registered["allowed_resources"]

        # Permitted operation
        req_ok = ActionRequest(
            action_id="act_dyn_01",
            agent_id="agent_audit",
            session_id="session_aud_01",
            task_id="task_audit_2026",
            operation="SELECT",
            resource="audit_log",
        )
        res_ok = evaluate_action(req_ok)
        assert res_ok.decision == "ALLOW"

        # Out-of-scope write
        req_bad = ActionRequest(
            action_id="act_dyn_02",
            agent_id="agent_audit",
            session_id="session_aud_01",
            task_id="task_audit_2026",
            operation="DELETE",
            resource="audit_log",
        )
        res_bad = evaluate_action(req_bad)
        assert res_bad.decision == "BLOCK"


class TestApplyDriftHook:
    """Test policy-drift combination rules."""

    def test_allow_upgraded_to_hold_on_high_drift(self):
        base_resp = EvaluateResponse(
            action_id="act_drift_01",
            decision="ALLOW",
            reason="Matches task policy",
            risk_score=0,
            executed=False,
        )
        upgraded = apply_drift(base_resp, drift_score=75)
        assert upgraded.decision == "HOLD"
        assert upgraded.risk_score == 75
        assert "Elevated behavioral risk" in upgraded.reason

    def test_allow_retains_allow_with_elevated_risk(self):
        base_resp = EvaluateResponse(
            action_id="act_drift_02",
            decision="ALLOW",
            reason="Matches task policy",
            risk_score=0,
            executed=False,
        )
        adjusted = apply_drift(base_resp, drift_score=45)
        assert adjusted.decision == "ALLOW"
        assert adjusted.risk_score == 45

    def test_block_never_softened_by_low_drift(self):
        base_resp = EvaluateResponse(
            action_id="act_drift_03",
            decision="BLOCK",
            reason="Write is outside declared scope",
            risk_score=100,
            executed=False,
        )
        result = apply_drift(base_resp, drift_score=5)
        assert result.decision == "BLOCK"
        assert result.risk_score == 100

    def test_hold_never_softened_by_low_drift(self):
        base_resp = EvaluateResponse(
            action_id="act_drift_04",
            decision="HOLD",
            reason="Additional authorization required",
            risk_score=60,
            executed=False,
        )
        result = apply_drift(base_resp, drift_score=0)
        assert result.decision == "HOLD"
        assert result.risk_score == 60


class TestTaskAPIEndpoints:
    """Test HTTP API endpoints for task registry."""

    def test_post_and_get_task_api(self, client):
        payload = {
            "task_id": "task_api_test",
            "agent_id": "agent_99",
            "purpose": "API integration test task",
            "allowed_operations": ["READ"],
            "allowed_resources": ["transactions"],
            "requires_review_for": ["UPDATE"],
        }
        res = client.post("/tasks", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["task_id"] == "task_api_test"
        assert data["status"] == "registered"

        # Verify GET /tasks
        get_res = client.get("/tasks")
        assert get_res.status_code == 200
        tasks = get_res.json()
        assert "task_api_test" in tasks

        # Verify GET /tasks/{task_id}
        single_res = client.get("/tasks/task_api_test")
        assert single_res.status_code == 200
        assert single_res.json()["task_id"] == "task_api_test"
