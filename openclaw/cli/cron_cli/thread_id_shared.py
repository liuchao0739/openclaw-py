"""Cron CLI parsing helpers for Telegram topic thread ids and session targets."""

from __future__ import annotations

import re
from typing import Any


def parse_cron_thread_id_option(value: Any) -> int | None:
    """Parse a --thread-id option value into a positive integer."""
    if value is None:
        return None
    raw = str(value).strip() if value is not None else ""
    if not raw:
        return None
    if not re.match(r"^\d+$", raw):
        raise ValueError("--thread-id must be a positive integer Telegram topic thread id")
    parsed = int(raw)
    if parsed <= 0:
        raise ValueError("--thread-id must be a safe positive integer Telegram topic thread id")
    return parsed


def normalize_cron_session_target_option(value: Any) -> str | None:
    """Normalize a --session-target option value.

    Accepts 'main', 'isolated', 'current', or 'session:<id>' formats.
    """
    if value is None:
        return None
    raw = str(value).strip() if value is not None else ""
    if not raw:
        return None
    lower = raw.lower()
    if lower in ("main", "isolated", "current"):
        return lower
    if lower.startswith("session:"):
        session_id = raw[8:].strip()
        return f"session:{session_id}" if session_id else None
    return None
