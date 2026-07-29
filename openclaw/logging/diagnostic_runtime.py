"""Diagnostic runtime helpers expose process runtime facts for diagnostics.

Mirrors src/logging/diagnostic-runtime.ts.
"""

from __future__ import annotations

import time
from typing import Any

from openclaw.logging.subsystem import create_subsystem_logger

_diag = create_subsystem_logger("diagnostic")
_last_activity_at = 0


def diagnostic_logger() -> dict[str, Any]:
    return _diag


def mark_diagnostic_activity() -> None:
    global _last_activity_at
    _last_activity_at = int(time.time() * 1000)


def get_last_diagnostic_activity_at() -> int:
    return _last_activity_at


def reset_diagnostic_activity_for_test() -> None:
    global _last_activity_at
    _last_activity_at = 0


def log_lane_enqueue(lane: str, queue_size: int) -> None:
    _diag["debug"](f"lane enqueue: lane={lane} queueSize={queue_size}")
    mark_diagnostic_activity()


def log_lane_dequeue(lane: str, wait_ms: int, queue_size: int) -> None:
    _diag["debug"](f"lane dequeue: lane={lane} waitMs={wait_ms} queueSize={queue_size}")
    mark_diagnostic_activity()


__all__ = [
    "diagnostic_logger",
    "mark_diagnostic_activity",
    "get_last_diagnostic_activity_at",
    "reset_diagnostic_activity_for_test",
    "log_lane_enqueue",
    "log_lane_dequeue",
]
