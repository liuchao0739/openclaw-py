from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from .timeouts import resolve_finite_timeout_delay_ms

DEFAULT_MAX_WAIT_MS = 10_000
DEFAULT_INTERVAL_MS = 1
DEFAULT_DRIFT_THRESHOLD_MS = 200
DEFAULT_CONSECUTIVE_READY_CHECKS = 2


@dataclass
class EventLoopReadyResult:
    ready: bool
    elapsed_ms: int
    max_drift_ms: int
    checks: int
    aborted: bool = False


@dataclass
class EventLoopReadyOptions:
    max_wait_ms: Optional[int] = None
    interval_ms: Optional[int] = None
    drift_threshold_ms: Optional[int] = None
    consecutive_ready_checks: Optional[int] = None
    abort_event: Optional[asyncio.Event] = None


def _resolve_positive_integer(value: Optional[int], fallback: int) -> int:
    if value is not None and value == int(value) and value > 0:
        return max(1, int(value))
    return fallback


async def wait_for_event_loop_ready(
    options: Optional[EventLoopReadyOptions] = None,
) -> EventLoopReadyResult:
    if options is None:
        options = EventLoopReadyOptions()

    max_wait_ms = resolve_finite_timeout_delay_ms(
        options.max_wait_ms, DEFAULT_MAX_WAIT_MS, min_ms=0
    )
    interval_ms = resolve_finite_timeout_delay_ms(
        options.interval_ms, DEFAULT_INTERVAL_MS
    )
    drift_threshold_ms = _resolve_positive_integer(
        options.drift_threshold_ms, DEFAULT_DRIFT_THRESHOLD_MS
    )
    consecutive_ready_checks = _resolve_positive_integer(
        options.consecutive_ready_checks, DEFAULT_CONSECUTIVE_READY_CHECKS
    )
    abort_event = options.abort_event

    started_at = time.monotonic()
    ready_checks = 0
    checks = 0
    max_drift_ms = 0

    if abort_event and abort_event.is_set():
        elapsed = int(max(0, (time.monotonic() - started_at) * 1000))
        return EventLoopReadyResult(
            ready=False,
            elapsed_ms=elapsed,
            max_drift_ms=max_drift_ms,
            checks=checks,
            aborted=True,
        )

    while True:
        if abort_event and abort_event.is_set():
            elapsed = int(max(0, (time.monotonic() - started_at) * 1000))
            return EventLoopReadyResult(
                ready=False,
                elapsed_ms=elapsed,
                max_drift_ms=max_drift_ms,
                checks=checks,
                aborted=True,
            )

        elapsed = int(max(0, (time.monotonic() - started_at) * 1000))
        remaining = max_wait_ms - elapsed
        if remaining <= 0:
            return EventLoopReadyResult(
                ready=False,
                elapsed_ms=elapsed,
                max_drift_ms=max_drift_ms,
                checks=checks,
                aborted=False,
            )

        delay_ms = min(interval_ms, remaining)
        scheduled_at = time.monotonic()
        await asyncio.sleep(delay_ms / 1000.0)

        checks += 1
        drift = int(max(0, (time.monotonic() - scheduled_at) * 1000 - delay_ms))
        max_drift_ms = max(max_drift_ms, drift)

        if drift > drift_threshold_ms:
            ready_checks = 0
        else:
            ready_checks += 1

        if ready_checks >= consecutive_ready_checks:
            elapsed = int(max(0, (time.monotonic() - started_at) * 1000))
            return EventLoopReadyResult(
                ready=True,
                elapsed_ms=elapsed,
                max_drift_ms=max_drift_ms,
                checks=checks,
                aborted=False,
            )
