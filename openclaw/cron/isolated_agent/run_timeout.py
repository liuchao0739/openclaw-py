"""Converts cron payload timeout overrides into embedded-runner timeout signals.

Mirrors src/cron/isolated-agent/run-timeout.ts.
"""

from __future__ import annotations

from typing import Any

# Timer-safe upper bound mirrors Node.js setTimeout (2^31 - 1 ms ≈ 24.8 days).
_TIMER_SAFE_MAX_MS = 2**31 - 1


def _finite_seconds_to_timer_safe_milliseconds(value: Any) -> int | None:
    """Convert a seconds value into a timer-safe millisecond integer.

    Returns ``None`` for non-finite, non-numeric, or boolean values.
    Values exceeding the timer-safe max are clamped to the max.
    """
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


def resolve_cron_run_timeout_override_ms(timeout_seconds: Any) -> int | None:
    """Convert explicit cron payload ``timeoutSeconds`` into a timer-safe ms override.

    Returns ``None`` when the value is not a finite number.
    """
    return _finite_seconds_to_timer_safe_milliseconds(timeout_seconds)
