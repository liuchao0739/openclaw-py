from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from .numeric_options import resolve_integer_option
from .types import AcpSession

DEFAULT_MAX_SESSIONS = 5_000
DEFAULT_IDLE_TTL_MS = 24 * 60 * 60 * 1_000


class AcpSessionStore:
    def create_session(
        self,
        session_key: str,
        cwd: str,
        session_id: str | None = None,
        ledger_session_id: str | None = None,
    ) -> AcpSession:
        ...

    def has_session(self, session_id: str) -> bool:
        ...

    def get_session(self, session_id: str) -> AcpSession | None:
        ...

    def get_session_by_run_id(self, run_id: str) -> AcpSession | None:
        ...

    def set_active_run(
        self, session_id: str, run_id: str, abort_controller: Any
    ) -> None:
        ...

    def clear_active_run(self, session_id: str) -> None:
        ...

    def cancel_active_run(self, session_id: str) -> bool:
        ...

    def delete_session(self, session_id: str) -> bool:
        ...

    def clear_all_sessions_for_test(self) -> None:
        ...


class _InMemorySessionStore(AcpSessionStore):
    def __init__(self, max_sessions: int, idle_ttl_ms: int, now: Callable[[], int]):
        self._max_sessions = max_sessions
        self._idle_ttl_ms = idle_ttl_ms
        self._now = now
        self._sessions: dict[str, AcpSession] = {}
        self._run_id_to_session_id: dict[str, str] = {}

    def _touch_session(self, session: AcpSession, now_ms: int) -> None:
        session["lastTouchedAt"] = now_ms

    def _remove_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        active_run_id = session.get("activeRunId")
        if active_run_id:
            self._run_id_to_session_id.pop(active_run_id, None)
        abort_controller = session.get("abortController")
        if abort_controller is not None:
            abort_controller.abort()
        del self._sessions[session_id]
        return True

    def _reap_idle_sessions(self, now_ms: int) -> None:
        idle_before = now_ms - self._idle_ttl_ms
        to_remove = []
        for session_id, session in self._sessions.items():
            if session.get("activeRunId") or session.get("abortController"):
                continue
            if session.get("lastTouchedAt", 0) > idle_before:
                continue
            to_remove.append(session_id)
        for session_id in to_remove:
            self._remove_session(session_id)

    def _evict_oldest_idle_session(self) -> bool:
        oldest_session_id: str | None = None
        oldest_last_touched_at = float("inf")
        for session_id, session in self._sessions.items():
            if session.get("activeRunId") or session.get("abortController"):
                continue
            if session.get("lastTouchedAt", 0) >= oldest_last_touched_at:
                continue
            oldest_last_touched_at = session.get("lastTouchedAt", 0)
            oldest_session_id = session_id
        if oldest_session_id is None:
            return False
        return self._remove_session(oldest_session_id)

    def create_session(
        self,
        session_key: str,
        cwd: str,
        session_id: str | None = None,
        ledger_session_id: str | None = None,
    ) -> AcpSession:
        now_ms = self._now()
        resolved_session_id = session_id or str(uuid.uuid4())
        existing_session = self._sessions.get(resolved_session_id)
        if existing_session is not None:
            existing_session["sessionKey"] = session_key
            if ledger_session_id is not None:
                existing_session["ledgerSessionId"] = ledger_session_id
            existing_session["cwd"] = cwd
            self._touch_session(existing_session, now_ms)
            return existing_session
        self._reap_idle_sessions(now_ms)
        if len(self._sessions) >= self._max_sessions and not self._evict_oldest_idle_session():
            raise RuntimeError(
                f"ACP session limit reached (max {self._max_sessions}). Close idle ACP clients and retry."
            )
        session: AcpSession = {
            "sessionId": resolved_session_id,
            "sessionKey": session_key,
            "cwd": cwd,
            "createdAt": now_ms,
            "lastTouchedAt": now_ms,
            "abortController": None,
            "activeRunId": None,
        }
        if ledger_session_id is not None:
            session["ledgerSessionId"] = ledger_session_id
        self._sessions[resolved_session_id] = session
        return session

    def has_session(self, session_id: str) -> bool:
        return session_id in self._sessions

    def get_session(self, session_id: str) -> AcpSession | None:
        session = self._sessions.get(session_id)
        if session is not None:
            self._touch_session(session, self._now())
        return session

    def get_session_by_run_id(self, run_id: str) -> AcpSession | None:
        session_id = self._run_id_to_session_id.get(run_id)
        if session_id is None:
            return None
        session = self._sessions.get(session_id)
        if session is not None:
            self._touch_session(session, self._now())
        return session

    def set_active_run(
        self, session_id: str, run_id: str, abort_controller: Any
    ) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        old_run_id = session.get("activeRunId")
        if old_run_id and old_run_id != run_id:
            self._run_id_to_session_id.pop(old_run_id, None)
        session["activeRunId"] = run_id
        session["abortController"] = abort_controller
        self._run_id_to_session_id[run_id] = session_id
        self._touch_session(session, self._now())

    def clear_active_run(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        old_run_id = session.get("activeRunId")
        if old_run_id:
            self._run_id_to_session_id.pop(old_run_id, None)
        session["activeRunId"] = None
        session["abortController"] = None
        self._touch_session(session, self._now())

    def cancel_active_run(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None or session.get("abortController") is None:
            return False
        session["abortController"].abort()
        old_run_id = session.get("activeRunId")
        if old_run_id:
            self._run_id_to_session_id.pop(old_run_id, None)
        session["abortController"] = None
        session["activeRunId"] = None
        self._touch_session(session, self._now())
        return True

    def delete_session(self, session_id: str) -> bool:
        return self._remove_session(session_id)

    def clear_all_sessions_for_test(self) -> None:
        for session in self._sessions.values():
            abort_controller = session.get("abortController")
            if abort_controller is not None:
                abort_controller.abort()
        self._sessions.clear()
        self._run_id_to_session_id.clear()


def create_in_memory_session_store(
    max_sessions: int | None = None,
    idle_ttl_ms: int | None = None,
    now: Callable[[], int] | None = None,
) -> AcpSessionStore:
    resolved_max = resolve_integer_option(max_sessions, DEFAULT_MAX_SESSIONS, min=1)
    resolved_ttl = resolve_integer_option(idle_ttl_ms, DEFAULT_IDLE_TTL_MS, min=1_000)
    resolved_now = now if now is not None else (lambda: int(time.time() * 1000))
    return _InMemorySessionStore(resolved_max, resolved_ttl, resolved_now)


default_acp_session_store = create_in_memory_session_store()