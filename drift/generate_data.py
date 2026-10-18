"""
drift/generate_data.py
======================
Generates deterministic synthetic agent-action scenarios for Agent Warden-Z.

Purpose:
    Provide realistic fake data for developing and testing the behavioral
    drift risk scorer.  No real customer data, secrets, or credentials
    are used.  All identifiers and transaction records are fictional.

Scenarios produced:
    A. Normal behaviour         — permitted reads within task scope
    B. Suspicious behaviour     — writes/exports/deletes outside scope,
                                  repeated unauthorized attempts
    C. Unusual-but-legitimate   — permitted but uncommon operations

Output:
    data/synthetic_agent_actions.json
    (also returned as a Python list by generate_scenarios())
"""

import json
import os
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Shared action-request fields (must match the project's shared contract)
# ---------------------------------------------------------------------------
# Required fields per shared schema:
#   action_id, agent_id, session_id, task_id, operation, resource
#
# Extra fields added by this module (do not conflict with shared schema):
#   timestamp, authorized_operations, authorized_resources,
#   policy_decision, label, notes

# ---------------------------------------------------------------------------
# Policy stubs
# Each agent has a declared task with explicitly authorized operations and
# resources.  The policy engine is the authoritative enforcer; these stubs
# are used only for synthetic-data labelling and local testing.
# ---------------------------------------------------------------------------
AGENT_POLICIES = {
    "agent_01": {
        "task_id": "task_001",
        "authorized_operations": ["READ"],
        "authorized_resources": [
            "transaction_TX1001",
            "transaction_TX1002",
            "transaction_TX1003",
        ],
    },
    "agent_02": {
        "task_id": "task_002",
        "authorized_operations": ["READ", "SUMMARIZE"],
        "authorized_resources": [
            "report_R001",
            "report_R002",
        ],
    },
}


def _ts(year: int, month: int, day: int, hour: int, minute: int) -> str:
    """Return an ISO-8601 UTC timestamp string."""
    dt = datetime(year, month, day, hour, minute, 0, tzinfo=timezone.utc)
    return dt.isoformat()


def generate_scenarios() -> list[dict]:
    """
    Return a list of synthetic action records.

    Every record contains the shared action-request fields plus metadata
    fields used for testing and labelling.

    Returns:
        list[dict]: A deterministic, reproducible list of action records.
    """
    scenarios = []

    # ==================================================================
    # A. NORMAL BEHAVIOUR — agent_01, session_01
    #    Agent reads approved resources within its declared task scope.
    # ==================================================================

    # A-1: Single permitted read
    scenarios.append({
        "action_id": "act_001",
        "agent_id": "agent_01",
        "session_id": "session_01",
        "task_id": "task_001",
        "operation": "READ",
        "resource": "transaction_TX1001",
        "timestamp": _ts(2026, 1, 10, 9, 0),
        "authorized_operations": ["READ"],
        "authorized_resources": ["transaction_TX1001", "transaction_TX1002", "transaction_TX1003"],
        "policy_decision": "ALLOW",
        "label": "NORMAL",
        "notes": "Permitted read within task scope.",
    })

    # A-2: Repeated legitimate reads — same agent, same session
    scenarios.append({
        "action_id": "act_002",
        "agent_id": "agent_01",
        "session_id": "session_01",
        "task_id": "task_001",
        "operation": "READ",
        "resource": "transaction_TX1002",
        "timestamp": _ts(2026, 1, 10, 9, 5),
        "authorized_operations": ["READ"],
        "authorized_resources": ["transaction_TX1001", "transaction_TX1002", "transaction_TX1003"],
        "policy_decision": "ALLOW",
        "label": "NORMAL",
        "notes": "Second permitted read in the same session.",
    })

    # A-3: Continuing within scope in a later session
    scenarios.append({
        "action_id": "act_003",
        "agent_id": "agent_01",
        "session_id": "session_02",
        "task_id": "task_001",
        "operation": "READ",
        "resource": "transaction_TX1003",
        "timestamp": _ts(2026, 1, 11, 10, 0),
        "authorized_operations": ["READ"],
        "authorized_resources": ["transaction_TX1001", "transaction_TX1002", "transaction_TX1003"],
        "policy_decision": "ALLOW",
        "label": "NORMAL",
        "notes": "Permitted read in a new session — consistent baseline.",
    })

    # ==================================================================
    # B. SUSPICIOUS BEHAVIOUR
    #    Operations outside declared scope, repeated across sessions.
    # ==================================================================

    # B-1: Unauthorized write attempt
    scenarios.append({
        "action_id": "act_004",
        "agent_id": "agent_01",
        "session_id": "session_03",
        "task_id": "task_001",
        "operation": "UPDATE",
        "resource": "transaction_TX1042",
        "timestamp": _ts(2026, 1, 12, 14, 0),
        "authorized_operations": ["READ"],
        "authorized_resources": ["transaction_TX1001", "transaction_TX1002", "transaction_TX1003"],
        "policy_decision": "BLOCK",
        "label": "SUSPICIOUS",
        "notes": "UPDATE is not in the agent's authorized operations.",
    })

    # B-2: Export attempt on a sensitive resource
    scenarios.append({
        "action_id": "act_005",
        "agent_id": "agent_01",
        "session_id": "session_03",
        "task_id": "task_001",
        "operation": "EXPORT",
        "resource": "transaction_TX1042",
        "timestamp": _ts(2026, 1, 12, 14, 5),
        "authorized_operations": ["READ"],
        "authorized_resources": ["transaction_TX1001", "transaction_TX1002", "transaction_TX1003"],
        "policy_decision": "BLOCK",
        "label": "SUSPICIOUS",
        "notes": "EXPORT is a high-risk operation and is not authorized.",
    })

    # B-3: Delete attempt
    scenarios.append({
        "action_id": "act_006",
        "agent_id": "agent_01",
        "session_id": "session_03",
        "task_id": "task_001",
        "operation": "DELETE",
        "resource": "transaction_TX1001",
        "timestamp": _ts(2026, 1, 12, 14, 10),
        "authorized_operations": ["READ"],
        "authorized_resources": ["transaction_TX1001", "transaction_TX1002", "transaction_TX1003"],
        "policy_decision": "BLOCK",
        "label": "SUSPICIOUS",
        "notes": "DELETE is not authorized and is an irreversible action.",
    })

    # B-4: Repeated unauthorized write in a LATER session (drift escalation)
    scenarios.append({
        "action_id": "act_007",
        "agent_id": "agent_01",
        "session_id": "session_04",
        "task_id": "task_001",
        "operation": "UPDATE",
        "resource": "transaction_TX9999",
        "timestamp": _ts(2026, 1, 13, 9, 0),
        "authorized_operations": ["READ"],
        "authorized_resources": ["transaction_TX1001", "transaction_TX1002", "transaction_TX1003"],
        "policy_decision": "BLOCK",
        "label": "SUSPICIOUS",
        "notes": "Repeating unauthorized UPDATE across sessions — escalation signal.",
    })

    # ==================================================================
    # C. UNUSUAL-BUT-LEGITIMATE BEHAVIOUR
    #    Permitted operation that is less common, but not a policy violation.
    # ==================================================================

    # C-1: agent_02 uses SUMMARIZE — authorized but infrequent
    scenarios.append({
        "action_id": "act_008",
        "agent_id": "agent_02",
        "session_id": "session_05",
        "task_id": "task_002",
        "operation": "SUMMARIZE",
        "resource": "report_R001",
        "timestamp": _ts(2026, 1, 14, 11, 0),
        "authorized_operations": ["READ", "SUMMARIZE"],
        "authorized_resources": ["report_R001", "report_R002"],
        "policy_decision": "ALLOW",
        "label": "UNUSUAL_BUT_LEGITIMATE",
        "notes": "SUMMARIZE is authorized; agent seldom uses it, but this is not a violation.",
    })

    # C-2: agent_01 accesses a different (but still authorized) resource
    scenarios.append({
        "action_id": "act_009",
        "agent_id": "agent_01",
        "session_id": "session_06",
        "task_id": "task_001",
        "operation": "READ",
        "resource": "transaction_TX1003",
        "timestamp": _ts(2026, 1, 15, 8, 30),
        "authorized_operations": ["READ"],
        "authorized_resources": ["transaction_TX1001", "transaction_TX1002", "transaction_TX1003"],
        "policy_decision": "ALLOW",
        "label": "UNUSUAL_BUT_LEGITIMATE",
        "notes": (
            "Agent usually reads TX1001; switching to TX1003 is a pattern change "
            "but does not violate policy."
        ),
    })

    return scenarios


def save_scenarios(output_path: str = None) -> str:
    """
    Save the synthetic scenarios to a JSON file.

    Args:
        output_path: Destination file path.  Defaults to
                     data/synthetic_agent_actions.json relative to this
                     file's parent directory.

    Returns:
        str: Absolute path of the file that was written.
    """
    if output_path is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(repo_root, "data", "synthetic_agent_actions.json")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    data = generate_scenarios()
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)

    return output_path


# ---------------------------------------------------------------------------
# Run directly: python drift/generate_data.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    path = save_scenarios()
    scenarios = generate_scenarios()

    print(f"Saved {len(scenarios)} synthetic scenarios to: {path}\n")
    print(f"{'ID':<10} {'Agent':<10} {'Session':<12} {'Operation':<12} {'Label':<30} {'Decision'}")
    print("-" * 90)
    for s in scenarios:
        print(
            f"{s['action_id']:<10} {s['agent_id']:<10} {s['session_id']:<12} "
            f"{s['operation']:<12} {s['label']:<30} {s['policy_decision']}"
        )
