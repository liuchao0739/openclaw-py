"""Log file shared helpers used by log file path and size cap logic.

Mirrors src/logging/log-file-shared.ts.
"""

from __future__ import annotations

from datetime import datetime

LOG_PREFIX = "openclaw"
LOG_SUFFIX = ".log"


def can_use_node_fs() -> bool:
    return True


def format_local_date(date: datetime | None = None) -> str:
    date = date or datetime.now()
    return f"{date.year:04d}-{date.month:02d}-{date.day:02d}"


__all__ = ["LOG_PREFIX", "LOG_SUFFIX", "can_use_node_fs", "format_local_date"]
