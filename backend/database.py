import hashlib
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Path to database file in the repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "zentrix.db"


def get_connection() -> sqlite3.Connection:
    """Return a short-lived SQLite connection configured with sqlite3.Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create database tables and seed synthetic initial data if empty."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                customer_id TEXT,
                amount REAL,
                status TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                event_id TEXT PRIMARY KEY,
                action_id TEXT,
                agent_id TEXT,
                session_id TEXT,
                task_id TEXT,
                operation TEXT,
                resource TEXT,
                decision TEXT,
                reason TEXT,
                risk_score INTEGER,
                executed INTEGER,
                timestamp TEXT
            )
        """)

        # Seed synthetic data ONLY if tables are empty
        cursor.execute("SELECT COUNT(*) FROM transactions")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO transactions (id, customer_id, amount, status) VALUES (?, ?, ?, ?)",
                [
                    ("TX1042", "CUST001", 250.00, "PENDING"),
                    ("TX1043", "CUST002", 1250.50, "COMPLETED"),
                    ("TX1044", "CUST001", 49.99, "COMPLETED"),
                    ("TX1045", "CUST003", 820.00, "PENDING"),
                ],
            )

        cursor.execute("SELECT COUNT(*) FROM customers")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO customers (id, name, email) VALUES (?, ?, ?)",
                [
                    ("CUST001", "Alice Smith", "alice.smith@example.com"),
                    ("CUST002", "Bob Jones", "bob.jones@example.com"),
                    ("CUST003", "Charlie Brown", "charlie.brown@example.com"),
                ],
            )

        conn.commit()


def reset_db() -> None:
    """Delete all database contents and re-seed synthetic data."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS audit_log")
        cursor.execute("DROP TABLE IF EXISTS transactions")
        cursor.execute("DROP TABLE IF EXISTS customers")
        conn.commit()
    init_db()


def execute_action(request: Any) -> bool:
    """
    Execute a whitelisted action against the database.

    Defense in depth: only operation SELECT and resource 'transactions' are allowed.
    Refuses writes and unapproved resources even if called by mistake.
    Returns True only if the operation succeeded, False otherwise.
    """
    try:
        if isinstance(request, dict):
            raw_op = request.get("operation", "")
            raw_res = request.get("resource", "")
        else:
            raw_op = getattr(request, "operation", "")
            raw_res = getattr(request, "resource", "")

        operation = str(raw_op).strip().upper() if raw_op else ""
        resource = str(raw_res).strip().lower() if raw_res else ""

        if operation == "SELECT" and resource in {"transactions"}:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM transactions")
                cursor.fetchall()
                return True
        return False
    except Exception:
        return False


def log_event(request: Any, response: Any, executed: bool | None = None) -> None:
    """Insert an audit row storing identifiers and decision reasons only."""
    def _val(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    action_id = _val(request, "action_id") or _val(response, "action_id")
    agent_id = _val(request, "agent_id")
    session_id = _val(request, "session_id")
    task_id = _val(request, "task_id")
    operation = _val(request, "operation")
    resource = _val(request, "resource")
    decision = _val(response, "decision")
    reason = _val(response, "reason")
    risk_score = _val(response, "risk_score", 0)

    if executed is None:
        executed_val = _val(response, "executed", False)
    else:
        executed_val = executed
    executed_int = 1 if executed_val else 0

    timestamp = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO audit_log (
                event_id, action_id, agent_id, session_id,
                task_id, operation, resource, decision, reason,
                risk_score, executed, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                action_id,
                agent_id,
                session_id,
                task_id,
                operation,
                resource,
                decision,
                reason,
                risk_score,
                executed_int,
                timestamp,
            ),
        )
        conn.commit()


def get_audit_log(limit: int = 100) -> list[dict]:
    """Return the most recent audit log entries, newest first."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC, rowid DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_agent_history(agent_id: str) -> list[dict]:
    """Return all audit rows for a specific agent, oldest first."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM audit_log WHERE agent_id = ? ORDER BY timestamp ASC, rowid ASC",
            (agent_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_transaction(tx_id: str) -> dict | None:
    """Return a single transaction row by ID, or None if not found."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (tx_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row is not None else None


def get_db_fingerprint() -> str:
    """Compute SHA-256 hash of all rows in transactions table ordered by id."""
    hasher = hashlib.sha256()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, customer_id, amount, status FROM transactions ORDER BY id ASC"
        )
        for row in cursor.fetchall():
            row_repr = f"{row['id']}|{row['customer_id']}|{row['amount']}|{row['status']}\n"
            hasher.update(row_repr.encode("utf-8"))
    return hasher.hexdigest()


if __name__ == "__main__":
    reset_db()
    print("TX1042:", get_transaction("TX1042"))
    print("DB Fingerprint:", get_db_fingerprint())
