"""ACP control-plane package — session actor queue, active turns, manager facade.

Mirrors src/acp/control-plane/.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


class SessionActorQueue:
    """Per-session async queue that serializes ACP runtime operations."""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._pending_by_session: dict[str, int] = {}

    def get_total_pending_count(self) -> int:
        """Return total pending operations across all sessions."""
        return sum(self._pending_by_session.values())

    def get_pending_count(self, actor_key: str) -> int:
        """Return pending operations for a specific session."""
        return self._pending_by_session.get(actor_key, 0)

    async def run(self, actor_key: str, op: Callable[[], Awaitable[T]]) -> T:
        """Run an operation serialized by actor key."""
        if actor_key not in self._locks:
            self._locks[actor_key] = asyncio.Lock()
        self._pending_by_session[actor_key] = self._pending_by_session.get(actor_key, 0) + 1
        try:
            async with self._locks[actor_key]:
                return await op()
        finally:
            pending = self._pending_by_session.get(actor_key, 1) - 1
            if pending <= 0:
                self._pending_by_session.pop(actor_key, None)
            else:
                self._pending_by_session[actor_key] = pending


# --- Active turns registry ---

_active_turn_keys: set[str] = set()


def _normalize_actor_key(session_key: str) -> str:
    """Normalize a session key into a canonical actor key."""
    return session_key.strip().lower() if isinstance(session_key, str) else ""


def mark_acp_turn_active(session_key: str) -> None:
    """Mark a session as currently running an ACP turn."""
    if not session_key:
        return
    _active_turn_keys.add(_normalize_actor_key(session_key))


def clear_acp_turn_active(session_key: str) -> None:
    """Clear the active-turn marker for a session."""
    if not session_key:
        return
    _active_turn_keys.discard(_normalize_actor_key(session_key))


def is_acp_turn_active(session_key: str) -> bool:
    """Return whether the process currently owns an in-flight ACP turn for a session."""
    if not session_key:
        return False
    return _normalize_actor_key(session_key) in _active_turn_keys


def reset_acp_active_turns_for_tests() -> None:
    """Clear active-turn state for isolated tests."""
    _active_turn_keys.clear()


# --- Manager singleton facade ---

_acp_session_manager_singleton: Any = None


def get_acp_session_manager() -> Any:
    """Return the process-wide ACP session manager singleton."""
    global _acp_session_manager_singleton
    if _acp_session_manager_singleton is None:
        _acp_session_manager_singleton = _AcpSessionManager()
    return _acp_session_manager_singleton


def reset_acp_session_manager_for_tests() -> None:
    """Reset the singleton for tests."""
    global _acp_session_manager_singleton
    _acp_session_manager_singleton = None


def set_acp_session_manager_for_tests(manager: Any) -> None:
    """Set a custom manager for tests."""
    global _acp_session_manager_singleton
    _acp_session_manager_singleton = manager


class _AcpSessionManager:
    """Minimal ACP session manager — manages session lifecycle and turn execution."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._queue = SessionActorQueue()
        self._turn_stats = {"completed": 0, "failed": 0, "total_ms": 0.0, "max_ms": 0.0}

    async def initialize_session(self, params: dict[str, Any]) -> dict[str, Any]:
        """Initialize or resume an ACP session."""
        session_key = params.get("sessionKey", "")
        agent = params.get("agent", "default")
        mode = params.get("mode", "interactive")
        meta = {
            "sessionKey": session_key,
            "agent": agent,
            "mode": mode,
            "state": "ready",
            "lastActivityAt": 0,
        }
        self._sessions[session_key] = meta
        return meta

    async def run_turn(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run one ACP prompt turn."""
        import time

        session_key = params.get("sessionKey", "")
        text = params.get("text", "")
        start = time.monotonic()

        async def _op() -> dict[str, Any]:
            mark_acp_turn_active(session_key)
            try:
                result = {"sessionKey": session_key, "text": text, "output": ""}
                return result
            finally:
                clear_acp_turn_active(session_key)

        try:
            result = await self._queue.run(session_key, _op)
            elapsed_ms = (time.monotonic() - start) * 1000
            self._turn_stats["completed"] += 1
            self._turn_stats["total_ms"] += elapsed_ms
            self._turn_stats["max_ms"] = max(self._turn_stats["max_ms"], elapsed_ms)
            return result
        except Exception:
            self._turn_stats["failed"] += 1
            raise

    async def close_session(self, params: dict[str, Any]) -> dict[str, Any]:
        """Close, reset, or clean up an ACP session."""
        session_key = params.get("sessionKey", "")
        discard = params.get("discardPersistentState", False)
        existed = session_key in self._sessions
        if existed and discard:
            del self._sessions[session_key]
        return {
            "runtimeClosed": existed,
            "metaCleared": existed and discard,
        }

    def get_observability_snapshot(self) -> dict[str, Any]:
        """Return process-local diagnostics counters."""
        completed = self._turn_stats["completed"]
        avg = self._turn_stats["total_ms"] / completed if completed > 0 else 0.0
        return {
            "runtimeCache": {
                "activeSessions": len(self._sessions),
                "idleTtlMs": 0,
                "evictedTotal": 0,
            },
            "turns": {
                "active": self._queue.get_total_pending_count(),
                "queueDepth": self._queue.get_total_pending_count(),
                "completed": completed,
                "failed": self._turn_stats["failed"],
                "averageLatencyMs": avg,
                "maxLatencyMs": self._turn_stats["max_ms"],
            },
            "errorsByCode": {},
        }
