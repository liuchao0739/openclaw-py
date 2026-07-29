"""Diagnostic phase helpers measure named phases and emit timing diagnostics.

Mirrors src/logging/diagnostic-phase.ts.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Iterator

_RECENT_PHASE_CAPACITY = 40
_active_phase_stack: list[dict[str, Any]] = []
_recent_phases: list[dict[str, Any]] = []


def _round_metric(value: float, digits: int = 1) -> float:
    if not isinstance(value, (int, float)):
        return 0
    factor = 10 ** digits
    return round(value * factor) / factor


def _push_recent_phase(snapshot: dict[str, Any]) -> None:
    _recent_phases.append(snapshot)
    if len(_recent_phases) > _RECENT_PHASE_CAPACITY:
        del _recent_phases[: len(_recent_phases) - _RECENT_PHASE_CAPACITY]


def get_current_diagnostic_phase() -> str | None:
    return _active_phase_stack[-1]["name"] if _active_phase_stack else None


def _resolve_recent_phase_limit(limit: int) -> int | None:
    if not isinstance(limit, (int, float)) or limit <= 0:
        return None
    return int(limit)


def get_recent_diagnostic_phases(limit: int = 8) -> list[dict[str, Any]]:
    resolved = _resolve_recent_phase_limit(limit)
    if resolved is None:
        return []
    return [dict(phase) for phase in _recent_phases[-resolved:]]


def record_diagnostic_phase(snapshot: dict[str, Any]) -> None:
    _push_recent_phase(snapshot)


@contextmanager
def with_diagnostic_phase(name: str, details: dict[str, Any] | None = None) -> Iterator[None]:
    import time as _time
    active = {
        "name": name,
        "startedAt": int(_time.time() * 1000),
        "startedWallMs": _time.perf_counter() * 1000,
        "details": details,
    }
    _active_phase_stack.append(active)
    try:
        yield
    finally:
        ended_at = int(_time.time() * 1000)
        duration_ms = _round_metric(_time.perf_counter() * 1000 - active["startedWallMs"], 1)
        _active_phase_stack[:] = [e for e in _active_phase_stack if e is not active]
        record_diagnostic_phase(
            {
                "name": name,
                "startedAt": active["startedAt"],
                "endedAt": ended_at,
                "durationMs": duration_ms,
                "details": active["details"],
            }
        )


def reset_diagnostic_phases_for_test() -> None:
    _active_phase_stack.clear()
    _recent_phases.clear()


__all__ = [
    "get_current_diagnostic_phase",
    "get_recent_diagnostic_phases",
    "record_diagnostic_phase",
    "with_diagnostic_phase",
    "reset_diagnostic_phases_for_test",
]
