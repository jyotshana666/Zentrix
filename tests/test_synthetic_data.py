"""
tests/test_synthetic_data.py
============================
Tests for drift/generate_data.py — the synthetic scenario generator.

Verifies:
  - The generator runs without errors.
  - Every required shared-schema field is present in each record.
  - All three labels are represented: NORMAL, SUSPICIOUS, UNUSUAL_BUT_LEGITIMATE.
  - Output is deterministic (same call → same results).
  - No real secrets or credentials are present.
  - No external service is needed.
"""

import json
import os
import pytest

from drift.generate_data import generate_scenarios, save_scenarios, AGENT_POLICIES

REQUIRED_FIELDS = {
    "action_id", "agent_id", "session_id",
    "task_id", "operation", "resource",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def scenarios():
    return generate_scenarios()


# ---------------------------------------------------------------------------
# Test: basic generation
# ---------------------------------------------------------------------------

class TestGeneration:

    def test_returns_a_list(self, scenarios):
        assert isinstance(scenarios, list), "generate_scenarios() must return a list."

    def test_non_empty(self, scenarios):
        assert len(scenarios) > 0, "generate_scenarios() must return at least one scenario."

    def test_all_records_are_dicts(self, scenarios):
        for s in scenarios:
            assert isinstance(s, dict), f"Every scenario must be a dict, got {type(s)}."

    def test_required_fields_present(self, scenarios):
        """Every record must have all shared-schema required fields."""
        for s in scenarios:
            missing = REQUIRED_FIELDS - s.keys()
            assert not missing, (
                f"Scenario {s.get('action_id')} is missing fields: {missing}"
            )

    def test_action_ids_are_unique(self, scenarios):
        ids = [s["action_id"] for s in scenarios]
        assert len(ids) == len(set(ids)), "action_id values must be unique."

    def test_labels_present(self, scenarios):
        """All three expected labels must exist in the dataset."""
        labels = {s.get("label") for s in scenarios}
        assert "NORMAL" in labels, "Dataset must contain NORMAL scenarios."
        assert "SUSPICIOUS" in labels, "Dataset must contain SUSPICIOUS scenarios."
        assert "UNUSUAL_BUT_LEGITIMATE" in labels, (
            "Dataset must contain UNUSUAL_BUT_LEGITIMATE scenarios."
        )


# ---------------------------------------------------------------------------
# Test: individual scenario content
# ---------------------------------------------------------------------------

class TestScenarioContent:

    def test_normal_scenarios_are_allowed(self, scenarios):
        normal = [s for s in scenarios if s.get("label") == "NORMAL"]
        assert normal, "At least one NORMAL scenario must exist."
        for s in normal:
            assert s.get("policy_decision") == "ALLOW", (
                f"NORMAL scenario {s['action_id']} must have policy_decision=ALLOW."
            )

    def test_suspicious_scenarios_are_blocked(self, scenarios):
        suspicious = [s for s in scenarios if s.get("label") == "SUSPICIOUS"]
        assert suspicious, "At least one SUSPICIOUS scenario must exist."
        for s in suspicious:
            assert s.get("policy_decision") == "BLOCK", (
                f"SUSPICIOUS scenario {s['action_id']} must have policy_decision=BLOCK."
            )

    def test_unusual_but_legitimate_are_allowed(self, scenarios):
        unusual = [s for s in scenarios if s.get("label") == "UNUSUAL_BUT_LEGITIMATE"]
        assert unusual, "At least one UNUSUAL_BUT_LEGITIMATE scenario must exist."
        for s in unusual:
            assert s.get("policy_decision") == "ALLOW", (
                f"UNUSUAL_BUT_LEGITIMATE scenario {s['action_id']} must be ALLOW "
                f"(unusual does not mean prohibited)."
            )

    def test_no_real_credentials(self, scenarios):
        """Synthetic data must not contain real secrets or passwords."""
        forbidden = ["password", "secret", "api_key", "token", "credential"]
        all_text = json.dumps(scenarios).lower()
        for kw in forbidden:
            assert kw not in all_text, (
                f"Synthetic data must not contain '{kw}'. Check for real credentials."
            )

    def test_all_operations_are_strings(self, scenarios):
        for s in scenarios:
            assert isinstance(s["operation"], str) and s["operation"].strip(), (
                f"Scenario {s['action_id']}: operation must be a non-empty string."
            )


# ---------------------------------------------------------------------------
# Test: reproducibility
# ---------------------------------------------------------------------------

class TestReproducibility:

    def test_deterministic_output(self):
        """Calling generate_scenarios() twice must produce identical results."""
        first = generate_scenarios()
        second = generate_scenarios()
        assert first == second, (
            "generate_scenarios() is not deterministic — results differ across calls."
        )

    def test_action_ids_stable(self):
        """Specific action IDs must remain stable (used by other tests)."""
        scenarios = generate_scenarios()
        ids = [s["action_id"] for s in scenarios]
        assert "act_001" in ids
        assert "act_004" in ids  # first suspicious


# ---------------------------------------------------------------------------
# Test: file output
# ---------------------------------------------------------------------------

class TestFileSave:

    def test_save_creates_file(self, tmp_path):
        out_path = str(tmp_path / "test_output.json")
        returned_path = save_scenarios(output_path=out_path)
        assert os.path.isfile(returned_path), "save_scenarios() must create the output file."

    def test_saved_file_is_valid_json(self, tmp_path):
        out_path = str(tmp_path / "test_output.json")
        save_scenarios(output_path=out_path)
        with open(out_path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert isinstance(data, list), "Saved JSON must be a list."
        assert len(data) > 0, "Saved JSON must not be empty."
