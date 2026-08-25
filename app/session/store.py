"""Session state management."""

from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Turn:
    role: str
    content: str

@dataclass
class Session:
    session_id: str
    turns: list[Turn] = field(default_factory=list)
    active_order_id: str | None = None
    active_topic: str | None = None

class SessionStore:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, session_id: str) -> Session:
        """Get an existing session or create a new one."""
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    def record_turn(self, session_id: str, role: str, content: str) -> None:
        """Record a single conversation turn."""
        session = self.get_or_create(session_id)
        session.turns.append(Turn(role=role, content=content))

    def set_active_order(self, session_id: str, order_id: str | None) -> None:
        """Set the active order ID context for the session (overwrites previous)."""
        session = self.get_or_create(session_id)
        session.active_order_id = order_id

    def set_active_topic(self, session_id: str, topic: str | None) -> None:
        """Set the active topic context for the session (overwrites previous)."""
        session = self.get_or_create(session_id)
        session.active_topic = topic

    def get_recent_turns(self, session_id: str, n: int = 6) -> list[Turn]:
        """Get the n most recent turns from the session."""
        session = self.get_or_create(session_id)
        return session.turns[-n:] if session.turns else []
