"""Queue state management for follow-up reply admission."""

from __future__ import annotations

from typing import Any

from openclaw.auto_reply.reply.queue.types import FollowupRun, QueueSettings


class QueueState:
    """Process-local queue state for follow-up reply admission."""

    def __init__(self) -> None:
        self._queues: dict[str, list[FollowupRun]] = {}
        self._active_run: dict[str, FollowupRun | None] = {}

    def get_queue(self, session_key: str) -> list[FollowupRun]:
        """Get the queue for a session key."""
        return self._queues.get(session_key, [])

    def set_queue(self, session_key: str, queue: list[FollowupRun]) -> None:
        """Set the queue for a session key."""
        self._queues[session_key] = queue

    def clear_queue(self, session_key: str) -> list[FollowupRun]:
        """Clear and return the queue for a session key."""
        return self._queues.pop(session_key, [])

    def get_active_run(self, session_key: str) -> FollowupRun | None:
        """Get the active run for a session key."""
        return self._active_run.get(session_key)

    def set_active_run(self, session_key: str, run: FollowupRun | None) -> None:
        """Set the active run for a session key."""
        self._active_run[session_key] = run

    def has_pending(self, session_key: str) -> bool:
        """Check if a session has pending queued runs."""
        return len(self.get_queue(session_key)) > 0

    def clear_all(self) -> None:
        """Clear all queues and active runs."""
        self._queues.clear()
        self._active_run.clear()


# Process-local singleton
_queue_state = QueueState()


def get_queue_state() -> QueueState:
    """Get the process-local queue state singleton."""
    return _queue_state


def reset_queue_state_for_tests() -> None:
    """Reset the queue state for tests."""
    global _queue_state
    _queue_state = QueueState()
