from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def diagnostic_event(
    event_type: str,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    return {
        "type": event_type,
        "args": list(args),
        "kwargs": kwargs,
        "timestamp": _now_iso(),
    }


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def format_diagnostic_event(event: dict[str, Any]) -> str:
    event_type = event.get("type", "unknown")
    timestamp = event.get("timestamp", "")
    args = event.get("args", [])
    kwargs = event.get("kwargs", {})
    parts = [f"[{timestamp}] {event_type}"]
    if args:
        parts.append(f"args={args}")
    if kwargs:
        parts.append(f"kwargs={kwargs}")
    return " ".join(parts)


def detect_error_kind(error: Exception) -> str:
    name = type(error).__name__.lower()
    msg = str(error).lower()

    if "timeout" in name or "timeout" in msg:
        return "timeout"
    if "rate" in msg or "429" in msg or "too many requests" in msg:
        return "rate_limit"
    if "auth" in name or "401" in msg or "403" in msg or "unauthorized" in msg:
        return "auth"
    if "network" in name or "connection" in name or "dns" in name:
        return "network"
    if "not found" in msg or "404" in msg:
        return "not_found"
    if "validation" in name or "invalid" in msg or "schema" in msg:
        return "validation"
    return "unknown"
