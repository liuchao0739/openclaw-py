"""Diagnostic payload helpers emit structured diagnostic events with normalized fields.

Mirrors src/logging/diagnostic-payload.ts.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from openclaw.infra.diagnostic_events import diagnostic_event


def log_large_payload(params: dict[str, Any]) -> None:
    diagnostic_event("payload.large", **params)


def log_rejected_large_payload(params: dict[str, Any]) -> None:
    log_large_payload({**params, "action": "rejected"})


def parse_content_length_header(raw: Any = None) -> int | None:
    if isinstance(raw, list):
        if not raw:
            return None
        value = raw[0]
    else:
        value = raw
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    if not trimmed or not re.match(r"^\d+$", trimmed):
        return None
    try:
        result = int(trimmed)
        return result if result >= 0 else None
    except ValueError:
        return None


__all__ = [
    "log_large_payload",
    "log_rejected_large_payload",
    "parse_content_length_header",
]
