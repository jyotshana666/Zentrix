"""
drift/session_history.py
========================
In-memory session history for Agent Warden-Z.

Purpose:
    Group, store, and retrieve agent-action events by agent ID and session ID.
    Supports comparing the current session with previous sessions for the same
    agent, which is the foundation for detecting behavioural drift.

Design rules:
    - Pure Python standard library — no external database required.
    - One SessionHistory object per runtime context (or per test).
    - Events from different agents are completely isolated.
    - Missing or malformed input is handled safely and does not crash the scorer.
    - Session order is determined by insertion order (Python dict guarantee,
      Python 3.7+).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


# ---------------------------------------------------------------------------
# Required fields every action record must have.
# These match the shared action-request schema.
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = {"action_id", "agent_id", "session_id", "operation", "resource"}


class SessionHistory:
    """
    Stores and retrieves action events grouped by agent and session.

    Internal structure:
        _data = {
            "agent_01": {
                "session_01": [ {action…}, {action…} ],
                "session_02": [ {action…} ],
            },
            "agent_02": {
                "session_05": [ {action…} ],
            },
        }

    Usage:
        history = SessionHistory()
        history.add_event(action_record)
        past = history.get_past_sessions(agent_id="agent_01",
                                         before_session_id="session_03")
    """

    def __init__(self) -> None:
        # Outer key: agent_id  →  Inner key: session_id  →  list of events
        self._data: dict[str, dict[str, list[dict]]] = defaultdict(
            lambda: defaultdict(list)
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_event(self, event: Any) -> tuple[bool, str]:
        """
        Add one action record to the history.

        Args:
            event: A dict containing at minimum the shared required fields.
                   Extra fields are preserved but not required.

        Returns:
            (True, "OK") on success.
            (False, reason_string) if the event is invalid and was skipped.
        """
        # Reject non-dict input
        if not isinstance(event, dict):
            return False, f"Event must be a dict, got {type(event).__name__}."

        # Check required fields
        missing = REQUIRED_FIELDS - event.keys()
        if missing:
            return False, f"Event missing required fields: {sorted(missing)}."

        # Reject blank agent_id or session_id
        agent_id = str(event.get("agent_id", "")).strip()
        session_id = str(event.get("session_id", "")).strip()
        if not agent_id:
            return False, "agent_id must not be empty."
        if not session_id:
            return False, "session_id must not be empty."

        # Store a shallow copy to avoid mutation surprises
        self._data[agent_id][session_id].append(dict(event))
        return True, "OK"

    def add_events(self, events: list[Any]) -> list[tuple[bool, str]]:
        """
        Add multiple events.  Returns a list of (success, message) tuples.

        Args:
            events: Iterable of action records.

        Returns:
            List of (bool, str) results, one per input event.
        """
        if not isinstance(events, (list, tuple)):
            return [(False, "events must be a list.")]
        return [self.add_event(e) for e in events]

    # ------------------------------------------------------------------
    # Reading — by agent
    # ------------------------------------------------------------------

    def get_all_sessions(self, agent_id: str) -> dict[str, list[dict]]:
        """
        Return all sessions for an agent in insertion order.

        Args:
            agent_id: The agent whose history to retrieve.

        Returns:
            Dict mapping session_id → list of events.
            Returns an empty dict if the agent has no history.
        """
        return dict(self._data.get(agent_id, {}))

    def get_session(self, agent_id: str, session_id: str) -> list[dict]:
        """
        Return all events for a specific agent + session.

        Returns:
            List of event dicts (may be empty).
        """
        return list(self._data.get(agent_id, {}).get(session_id, []))

    def get_past_sessions(
        self, agent_id: str, before_session_id: str
    ) -> dict[str, list[dict]]:
        """
        Return sessions that were recorded before a given session ID.

        "Before" is defined by insertion order — sessions added to history
        earlier come first.  This is used by the risk scorer to compare
        the current session against prior behaviour.

        Args:
            agent_id:          The agent whose history to examine.
            before_session_id: Only sessions inserted before this one are
                               returned.  If this session ID is not found,
                               all known sessions are returned.

        Returns:
            Ordered dict of {session_id: [events]} for prior sessions only.
        """
        all_sessions = self._data.get(agent_id, {})
        past: dict[str, list[dict]] = {}
        for sid, events in all_sessions.items():
            if sid == before_session_id:
                break
            past[sid] = list(events)
        return past

    def get_all_events_for_agent(self, agent_id: str) -> list[dict]:
        """
        Return every event for an agent across all sessions, in order.

        Returns:
            Flat list of event dicts.
        """
        result = []
        for events in self._data.get(agent_id, {}).values():
            result.extend(events)
        return result

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def known_agents(self) -> list[str]:
        """Return a sorted list of agent IDs currently in the history."""
        return sorted(self._data.keys())

    def session_count(self, agent_id: str) -> int:
        """Return the number of sessions recorded for an agent."""
        return len(self._data.get(agent_id, {}))

    def event_count(self, agent_id: str, session_id: str = None) -> int:
        """
        Return the number of events for an agent, optionally filtered by session.

        Args:
            agent_id:   Target agent.
            session_id: If provided, count only events in that session.
                        If None, count events across all sessions.
        """
        if session_id is not None:
            return len(self._data.get(agent_id, {}).get(session_id, []))
        return sum(
            len(evts) for evts in self._data.get(agent_id, {}).values()
        )

    def clear(self, agent_id: str = None) -> None:
        """
        Clear history.

        Args:
            agent_id: If provided, clear only that agent's history.
                      If None, clear all history.
        """
        if agent_id is not None:
            self._data.pop(agent_id, None)
        else:
            self._data.clear()

    def __repr__(self) -> str:
        summary = {
            agent: {sid: len(evts) for sid, evts in sessions.items()}
            for agent, sessions in self._data.items()
        }
        return f"SessionHistory({summary})"


# ---------------------------------------------------------------------------
# Quick demonstration — run: python drift/session_history.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from drift.generate_data import generate_scenarios

    history = SessionHistory()
    scenarios = generate_scenarios()

    results = history.add_events(scenarios)
    ok = sum(1 for ok, _ in results if ok)
    failed = [(msg, r) for ok, r, msg in
              [(ok, r, s.get("action_id", "?")) for (ok, r), s in zip(results, scenarios)]
              if not ok]

    print(f"Loaded {ok}/{len(scenarios)} events into session history.")
    print(f"History state: {history}\n")

    for agent in history.known_agents():
        sessions = history.get_all_sessions(agent)
        print(f"Agent: {agent}  ({history.session_count(agent)} sessions, "
              f"{history.event_count(agent)} total events)")
        for sid, evts in sessions.items():
            ops = [e["operation"] for e in evts]
            labels = [e.get("label", "?") for e in evts]
            print(f"  {sid}: {ops}  labels={labels}")

    print("\nPast sessions for agent_01 before session_03:")
    past = history.get_past_sessions("agent_01", before_session_id="session_03")
    for sid, evts in past.items():
        print(f"  {sid}: {[e['operation'] for e in evts]}")
