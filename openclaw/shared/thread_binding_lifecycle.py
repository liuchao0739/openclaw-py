"""Thread binding lifecycle for channel thread binding expiration."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class ThreadBindingLifecycleRecord:
    bound_at: int
    last_activity_at: int
    idle_timeout_ms: int | None = None
    max_age_ms: int | None = None


def _resolve_non_negative_integer(value: Any, default: int) -> int:
    if isinstance(value, (int, float)) and value >= 0:
        return max(0, int(value))
    return default


def resolve_thread_binding_lifecycle(
    record: ThreadBindingLifecycleRecord,
    default_idle_timeout_ms: int,
    default_max_age_ms: int,
) -> dict[str, Any]:
    idle_timeout = _resolve_non_negative_integer(record.idle_timeout_ms, default_idle_timeout_ms)
    max_age = _resolve_non_negative_integer(record.max_age_ms, default_max_age_ms)

    inactivity_expires_at = None
    if idle_timeout > 0:
        inactivity_expires_at = max(record.last_activity_at, record.bound_at) + idle_timeout

    max_age_expires_at = None
    if max_age > 0:
        max_age_expires_at = record.bound_at + max_age

    if inactivity_expires_at is not None and max_age_expires_at is not None:
        if inactivity_expires_at <= max_age_expires_at:
            return {"expires_at": inactivity_expires_at, "reason": "idle-expired"}
        return {"expires_at": max_age_expires_at, "reason": "max-age-expired"}
    if inactivity_expires_at is not None:
        return {"expires_at": inactivity_expires_at, "reason": "idle-expired"}
    if max_age_expires_at is not None:
        return {"expires_at": max_age_expires_at, "reason": "max-age-expired"}
    return {}
