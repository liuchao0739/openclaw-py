"""Log level constants define accepted logger levels and ordering.

Mirrors src/logging/levels.ts.
"""

from __future__ import annotations

from typing import Literal

ALLOWED_LOG_LEVELS = ("silent", "fatal", "error", "warn", "info", "debug", "trace")
LogLevel = Literal["silent", "fatal", "error", "warn", "info", "debug", "trace"]


def try_parse_log_level(level: str | None) -> LogLevel | None:
    if not isinstance(level, str):
        return None
    candidate = level.strip()
    return candidate if candidate in ALLOWED_LOG_LEVELS else None


def normalize_log_level(level: str | None = None, fallback: LogLevel = "info") -> LogLevel:
    parsed = try_parse_log_level(level)
    return parsed if parsed is not None else fallback


def level_to_min_level(level: LogLevel) -> int:
    mapping: dict[LogLevel, int] = {
        "trace": 1,
        "debug": 2,
        "info": 3,
        "warn": 4,
        "error": 5,
        "fatal": 6,
        "silent": float("inf"),
    }
    return mapping[level]


__all__ = [
    "ALLOWED_LOG_LEVELS",
    "LogLevel",
    "try_parse_log_level",
    "normalize_log_level",
    "level_to_min_level",
]
