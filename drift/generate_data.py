
"""
drift/generate_data.py

Generates deterministic synthetic agent-action scenarios for Agent Warden-Z.

All records are fictional and intended for development and testing.
"""

import json
import os
from datetime import datetime, timezone


# ---------------------------------------------------------
# Agent policies used to label the synthetic scenarios
# ---------------------------------------------------------

AGENT_POLICIES = {
    "agent_01": {
        "task_id": "task_001",
        "authorized_operations": ["SELECT"],
        "authorized_resources": [
            "transaction_TX1001",
            "transaction_TX1002",
            "transaction_TX1003",
        ],
    },
    "agent_02": {
        "task_id": "task_002",
        "authorized_operations": ["SELECT"],
        "authorized_resources": [
            "report_R001",
            "report_R002",
        ],
    },
}


def _ts(year: int, month: int, day: int, hour: int, minute: int) -> str:
    """Return an ISO-8601 UTC timestamp."""
    dt = datetime(year, month, day, hour, minute, 0, tzinfo=timezone.utc)
    return dt.isoformat()


def generate_scenarios() -> list[dict]:
    """Return a deterministic list of synthetic agent-action records."""

    scenarios = []

    # =====================================================
    # A. NORMAL BEHAVIOR
    # =====================================================

    scenarios.append({
        "action_id": "act_001",
        "agent_id": "agent_01",
        "session_id": "session_01",
        "task_id": "task_001",
        "operation": "SELECT",
        "resource": "transaction_TX1001",
        "timestamp": _ts(2026, 1, 10, 9, 0),
        "authorized_operations": ["SELECT"],
        "authorized_resources": [
            "transaction_TX1001",
            "transaction_TX1002",
            "transaction_TX1003",
        ],
        "policy_decision": "ALLOW",
        "label": "NORMAL",
        "notes": "Permitted SELECT within task scope.",
    })

    scenarios.append({
        "action_id": "act_002",
        "agent_id": "agent_01",
        "session_id": "session_01",
        "task_id": "task_001",
        "operation": "SELECT",
        "resource": "transaction_TX1002",
        "timestamp": _ts(2026, 1, 10, 9, 5),
        "authorized_operations": ["SELECT"],
        "authorized_resources": [
            "transaction_TX1001",
            "transaction_TX1002",
            "transaction_TX1003",
        ],
        "policy_decision": "ALLOW",
        "label": "NORMAL",
        "notes": "Second permitted SELECT in the same session.",
    })

    scenarios.append({
        "action_id": "act_003",
        "agent_id": "agent_01",
        "session_id": "session_02",
        "task_id": "task_001",
        "operation": "SELECT",
        "resource": "transaction_TX1003",
        "timestamp": _ts(2026, 1, 11, 10, 0),
        "authorized_operations": ["SELECT"],
        "authorized_resources": [
            "transaction_TX1001",
            "transaction_TX1002",
            "transaction_TX1003",
        ],
        "policy_decision": "ALLOW",
        "label": "NORMAL",
        "notes": "Permitted SELECT in a new session; consistent baseline.",
    })

    # =====================================================
    # B. SUSPICIOUS BEHAVIOR
    # Unauthorized actions across multiple sessions.
    # =====================================================

    scenarios.append({
        "action_id": "act_004",
        "agent_id": "agent_01",
        "session_id": "session_03",
        "task_id": "task_001",
        "operation": "UPDATE",
        "resource": "transaction_TX1042",
        "timestamp": _ts(2026, 1, 12, 14, 0),
        "authorized_operations": ["SELECT"],
        "authorized_resources": [
            "transaction_TX1001",
            "transaction_TX1002",
            "transaction_TX1003",
        ],
        "policy_decision": "BLOCK",
        "label": "SUSPICIOUS",
        "notes": "UPDATE is not an authorized operation.",
    })

    scenarios.append({
        "action_id": "act_005",
        "agent_id": "agent_01",
        "session_id": "session_03",
        "task_id": "task_001",
        "operation": "EXPORT",
        "resource": "transaction_TX1042",
        "timestamp": _ts(2026, 1, 12, 14, 5),
        "authorized_operations": ["SELECT"],
        "authorized_resources": [
            "transaction_TX1001",
            "transaction_TX1002",
            "transaction_TX1003",
        ],
        "policy_decision": "BLOCK",
        "label": "SUSPICIOUS",
        "notes": "EXPORT is unauthorized and potentially high risk.",
    })

    scenarios.append({
        "action_id": "act_006",
        "agent_id": "agent_01",
        "session_id": "session_03",
        "task_id": "task_001",
        "operation": "DELETE",
        "resource": "transaction_TX1001",
        "timestamp": _ts(2026, 1, 12, 14, 10),
        "authorized_operations": ["SELECT"],
        "authorized_resources": [
            "transaction_TX1001",
            "transaction_TX1002",
            "transaction_TX1003",
        ],
        "policy_decision": "BLOCK",
        "label": "SUSPICIOUS",
        "notes": "DELETE is unauthorized and could be irreversible.",
    })

    scenarios.append({
        "action_id": "act_007",
        "agent_id": "agent_01",
        "session_id": "session_04",
        "task_id": "task_001",
        "operation": "UPDATE",
        "resource": "transaction_TX9999",
        "timestamp": _ts(2026, 1, 13, 9, 0),
        "authorized_operations": ["SELECT"],
        "authorized_resources": [
            "transaction_TX1001",
            "transaction_TX1002",
            "transaction_TX1003",
        ],
        "policy_decision": "BLOCK",
        "label": "SUSPICIOUS",
        "notes": "Unauthorized UPDATE repeats in a later session, indicating possible behavioral drift.",
    })

    # =====================================================
    # C. UNUSUAL-BUT-LEGITIMATE BEHAVIOR
    # The action is permitted but differs from the usual
    # resource access pattern.
    # =====================================================

    scenarios.append({
        "action_id": "act_008",
        "agent_id": "agent_02",
        "session_id": "session_05",
        "task_id": "task_002",
        "operation": "SELECT",
        "resource": "report_R001",
        "timestamp": _ts(2026, 1, 14, 11, 0),
        "authorized_operations": ["SELECT"],
        "authorized_resources": [
            "report_R001",
            "report_R002",
        ],
        "policy_decision": "ALLOW",
        "label": "UNUSUAL_BUT_LEGITIMATE",
        "notes": "Authorized report SELECT that is uncommon for this agent.",
    })

    scenarios.append({
        "action_id": "act_009",
        "agent_id": "agent_01",
        "session_id": "session_06",
        "task_id": "task_001",
        "operation": "SELECT",
        "resource": "transaction_TX1003",
        "timestamp": _ts(2026, 1, 15, 8, 30),
        "authorized_operations": ["SELECT"],
        "authorized_resources": [
            "transaction_TX1001",
            "transaction_TX1002",
            "transaction_TX1003",
        ],
        "policy_decision": "ALLOW",
        "label": "UNUSUAL_BUT_LEGITIMATE",
        "notes": (
            "The agent accesses a different but authorized transaction. "
            "This is a pattern change, not a policy violation."
        ),
    })

    return scenarios


def save_scenarios(output_path: str = None) -> str:
    """Save synthetic scenarios as JSON and return the absolute file path."""

    if output_path is None:
        repo_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        output_path = os.path.join(
            repo_root,
            "data",
            "synthetic_agent_actions.json",
        )

    output_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(output_dir, exist_ok=True)

    data = generate_scenarios()

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return os.path.abspath(output_path)


if __name__ == "__main__":
    path = save_scenarios()
    scenarios = generate_scenarios()

    print(f"Saved {len(scenarios)} synthetic scenarios to: {path}\n")
    print(
        f"{'ID':<10} {'Agent':<10} {'Session':<12} "
        f"{'Operation':<12} {'Label':<30} {'Decision'}"
    )
    print("-" * 90)

    for scenario in scenarios:
        print(
            f"{scenario['action_id']:<10} "
            f"{scenario['agent_id']:<10} "
            f"{scenario['session_id']:<12} "
            f"{scenario['operation']:<12} "
            f"{scenario['label']:<30} "
            f"{scenario['policy_decision']}"
        )
