"""Env log level helpers normalize log level values from environment variables.

Mirrors src/logging/env-log-level.ts.
"""

from __future__ import annotations

import os

from openclaw.logging.levels import ALLOWED_LOG_LEVELS, LogLevel, try_parse_log_level
from openclaw.logging.state import logging_state


def resolve_env_log_level_override() -> LogLevel | None:
    trimmed = (os.environ.get("OPENCLAW_LOG_LEVEL") or "").strip()
    if not trimmed:
        logging_state.invalid_env_log_level_value = None
        return None
    parsed = try_parse_log_level(trimmed)
    if parsed:
        logging_state.invalid_env_log_level_value = None
        return parsed
    if logging_state.invalid_env_log_level_value != trimmed:
        logging_state.invalid_env_log_level_value = trimmed
        os.write(2, f'[openclaw] Ignoring invalid OPENCLAW_LOG_LEVEL="{trimmed}" (allowed: {"|".join(ALLOWED_LOG_LEVELS)}).\n'.encode())
    return None


__all__ = ["resolve_env_log_level_override"]
