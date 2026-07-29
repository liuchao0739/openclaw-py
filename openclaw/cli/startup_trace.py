from __future__ import annotations

from typing import Any

_startup_traces: list[dict] = []


def trace_startup_event(event: str, data: dict | None = None) -> None:
    _startup_traces.append({"event": event, "data": data or {}})


def get_startup_traces() -> list[dict]:
    return list(_startup_traces)


def clear_startup_traces() -> None:
    _startup_traces.clear()
