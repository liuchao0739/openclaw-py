"""HTTP server session fixtures shared by gateway session tests.

Mirrors src/gateway/test/server-sessions.test-helpers.ts. Only the pure
helper functions are ported; the vitest mock harness is deferred.
"""

from __future__ import annotations

import json
import time
from typing import Any, Generic, TypeVar

T = TypeVar("T")


def create_linear_session_transcript(session_id: str, contents: list[str]) -> str:
    """Build a linear JSONL session transcript from a list of message contents."""
    records: list[dict[str, Any]] = [
        {
            "type": "session",
            "version": 3,
            "id": session_id,
            "timestamp": "2026-06-19T12:00:00.000Z",
            "cwd": "/tmp",
        }
    ]
    for index, content in enumerate(contents):
        records.append(
            {
                "type": "message",
                "id": f"{session_id}-entry-{index}",
                "parentId": None if index == 0 else f"{session_id}-entry-{index - 1}",
                "timestamp": f"2026-06-19T12:00:{str(index + 1).zfill(2)}.000Z",
                "message": {"role": "user", "content": content, "timestamp": index + 1},
            }
        )
    return "\n".join(json.dumps(record) for record in records) + "\n"


class Deferred(Generic[T]):
    """A simple deferred/promise helper."""

    def __init__(self) -> None:
        self._resolved = False
        self._rejected = False
        self._value: T | None = None
        self._error: Any = None
        self._callbacks: list[callable] = []
        self._errbacks: list[callable] = []

    def resolve(self, value: T | None = None) -> None:
        if self._resolved or self._rejected:
            return
        self._resolved = True
        self._value = value
        for cb in self._callbacks:
            cb(value)
        self._callbacks.clear()

    def reject(self, reason: Any = None) -> None:
        if self._resolved or self._rejected:
            return
        self._rejected = True
        self._error = reason
        for eb in self._errbacks:
            eb(reason)
        self._errbacks.clear()

    @property
    def resolved(self) -> bool:
        return self._resolved

    @property
    def rejected(self) -> bool:
        return self._rejected


def create_deferred() -> Deferred:
    """Create a deferred resolver/rejecter pair."""
    return Deferred()


def session_store_entry(
    session_id: str, overrides: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build a session store entry fixture."""
    entry: dict[str, Any] = {
        "sessionId": session_id,
        "updatedAt": int(time.time() * 1000),
    }
    if overrides:
        entry.update(overrides)
    return entry


def is_internal_hook_event(value: Any) -> bool:
    """Type guard for InternalHookEvent."""
    if not isinstance(value, dict):
        return False
    return (
        isinstance(value.get("type"), str)
        and isinstance(value.get("action"), str)
        and isinstance(value.get("sessionKey"), str)
        and isinstance(value.get("messages"), list)
        and isinstance(value.get("context"), dict)
    )
