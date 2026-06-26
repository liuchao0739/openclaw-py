"""Resolves cron job wall-clock timeout policy.

Mirrors src/cron/service/timeout-policy.ts.
"""

from __future__ import annotations

from typing import Any, Mapping

# Timer-safe upper bound mirrors Node.js setTimeout (2^31 - 1 ms).
_TIMER_SAFE_MAX_MS = 2**31 - 1

DEFAULT_JOB_TIMEOUT_MS = 10 * 60_000  # 10 minutes
AGENT_TURN_SAFETY_TIMEOUT_MS = 60 * 60_000  # 60 minutes


def _finite_seconds_to_timer_safe_milliseconds(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        seconds = value
    elif isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        seconds = value
    else:
        return None
    ms = int(seconds * 1000)
    if ms < 0:
        return 0
    if ms > _TIMER_SAFE_MAX_MS:
        return _TIMER_SAFE_MAX_MS
    return ms


def resolve_cron_job_timeout_ms(job: Mapping[str, Any]) -> int | None:
    """Resolve the wall-clock timeout for a cron job.

    Includes explicit detached-run overrides from ``payload.timeoutSeconds``.
    Returns ``None`` when the configured timeout is <= 0 (disabled).
    Falls back to ``AGENT_TURN_SAFETY_TIMEOUT_MS`` for agent turns or
    ``DEFAULT_JOB_TIMEOUT_MS`` for other payloads when no override is set.
    """
    payload = job.get("payload")
    payload_kind = payload.get("kind") if isinstance(payload, Mapping) else None
    configured_timeout_ms: int | None = None
    if payload_kind in ("agentTurn", "command") and isinstance(payload, Mapping):
        timeout_seconds = payload.get("timeoutSeconds")
        if isinstance(timeout_seconds, (int, float)) and not isinstance(timeout_seconds, bool):
            configured_timeout_ms = _finite_seconds_to_timer_safe_milliseconds(timeout_seconds)

    if configured_timeout_ms is None:
        return AGENT_TURN_SAFETY_TIMEOUT_MS if payload_kind == "agentTurn" else DEFAULT_JOB_TIMEOUT_MS
    return configured_timeout_ms if configured_timeout_ms > 0 else None
