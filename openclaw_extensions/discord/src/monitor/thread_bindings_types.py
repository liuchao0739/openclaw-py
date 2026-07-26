"""Discord type declarations define plugin contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ThreadBindingTargetKind = Literal["subagent", "acp"]


@dataclass
class ThreadBindingRecord:
    account_id: str
    channel_id: str
    thread_id: str
    target_kind: ThreadBindingTargetKind
    target_session_key: str
    agent_id: str
    bound_by: str
    bound_at: int
    last_activity_at: int
    label: str | None = None
    webhook_id: str | None = None
    webhook_token: str | None = None
    idle_timeout_ms: int | None = None
    max_age_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


DEFAULT_THREAD_BINDING_IDLE_TIMEOUT_MS = 24 * 60 * 60 * 1000
DEFAULT_THREAD_BINDING_MAX_AGE_MS = 0

__all__ = [
    "DEFAULT_THREAD_BINDING_IDLE_TIMEOUT_MS",
    "DEFAULT_THREAD_BINDING_MAX_AGE_MS",
    "ThreadBindingRecord",
    "ThreadBindingTargetKind",
]
