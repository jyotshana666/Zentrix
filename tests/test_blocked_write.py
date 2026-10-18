"""
tests/test_blocked_write.py
===========================
Verifies Member 3's core security guarantee:
  1. A prohibited write action is stopped by the gateway before reaching the database.
  2. The target database record remains completely unchanged.
  3. The database cryptographic fingerprint (SHA-256) is identical before and after.
  4. The audit log contains a full explainable record with executed=False.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.database import (
    get_audit_log,
    get_db_fingerprint,
    get_transaction,
    reset_db,
)


@pytest.fixture(autouse=True)
def clean_database():
    """Ensure clean baseline database before each test run."""
    reset_db()
    yield
    reset_db()


@pytest.fixture
def client():
    return TestClient(app)


class TestBlockedWriteIntegrity:
    """Rigorous verification of pre-execution blocking and data integrity."""

    def test_prd_use_case_b_out_of_scope_write_blocked_and_unaltered(self, client):
        """
        PRD Use Case B:
          Agent is assigned task_001 (read-only investigation of TX1042).
          Agent proposes an UPDATE operation on transaction_TX1042.
          Expected outcome:
            - Intercepted before DB execution.
            - Decision is BLOCK.
            - executed flag is False.
            - TX1042 amount (250.0) and status ('PENDING') are unchanged.
            - DB fingerprint is 100% identical.
        """
        # Baseline state capture
        before_tx = get_transaction("TX1042")
        assert before_tx is not None
        assert before_tx["amount"] == 250.00
        assert before_tx["status"] == "PENDING"
        fingerprint_before = get_db_fingerprint()

        # Propose prohibited write
        payload = {
            "action_id": "act_uc_b_01",
            "agent_id": "agent_01",
            "session_id": "sess_02",
            "task_id": "task_001",
            "operation": "UPDATE",
            "resource": "transaction_TX1042",
        }

        response = client.post("/actions/execute", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["decision"] == "BLOCK"
        assert data["executed"] is False
        assert data["risk_score"] == 100
        assert "not permitted" in data["reason"].lower()

        # Verify database state remained unchanged
        after_tx = get_transaction("TX1042")
        assert after_tx == before_tx
        assert after_tx["status"] == "PENDING"
        assert after_tx["amount"] == 250.00

        fingerprint_after = get_db_fingerprint()
        assert fingerprint_after == fingerprint_before, "Database fingerprint must not change on blocked write"

        # Verify audit record integrity
        audit_records = get_audit_log(limit=5)
        matched = [a for a in audit_records if a["action_id"] == "act_uc_b_01"]
        assert len(matched) == 1
        record = matched[0]
        assert record["decision"] == "BLOCK"
        assert record["executed"] == 0
        assert record["operation"] == "UPDATE"
        assert record["resource"] == "transaction_TX1042"

    def test_direct_delete_operation_blocked(self, client):
        """High-risk DELETE operation on read-only task must be blocked with identical DB fingerprint."""
        fp_before = get_db_fingerprint()

        payload = {
            "action_id": "act_del_99",
            "agent_id": "agent_01",
            "session_id": "sess_02",
            "task_id": "task_read_transaction",
            "operation": "DELETE",
            "resource": "transactions",
        }

        resp = client.post("/actions/execute", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "BLOCK"
        assert data["executed"] is False

        fp_after = get_db_fingerprint()
        assert fp_after == fp_before
