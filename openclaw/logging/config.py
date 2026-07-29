"""Logging config helpers read and normalize logger configuration.

Mirrors src/logging/config.ts.
"""

from __future__ import annotations

import json
import os
from typing import Any

from openclaw.packages.normalization_core.record_coerce import is_record

_cached_logging_config: dict[str, Any] | None = None


def _resolve_config_path() -> str:
    return os.environ.get("OPENCLAW_CONFIG_PATH") or os.path.expanduser("~/.openclaw/config.json")


def should_skip_mutating_logging_config_read(argv: list[str] | None = None) -> bool:
    argv = argv or list(os.sys.argv) if hasattr(os, "sys") else []
    if len(argv) < 2:
        return False
    primary = argv[1] if len(argv) > 1 else ""
    secondary = argv[2] if len(argv) > 2 else ""
    return primary == "config" and secondary in ("schema", "validate")


def read_logging_config() -> dict[str, Any] | None:
    global _cached_logging_config
    if should_skip_mutating_logging_config_read():
        return None
    try:
        config_path = _resolve_config_path()
        if _cached_logging_config and _cached_logging_config.get("path") == config_path:
            return _cached_logging_config.get("logging")
        if not os.path.exists(config_path):
            return None
        with open(config_path, "r", encoding="utf-8") as f:
            parsed = json.load(f)
        logging = parsed.get("logging") if is_record(parsed) else None
        resolved = logging if is_record(logging) else None
        _cached_logging_config = {"path": config_path, "logging": resolved}
        return resolved
    except Exception:
        return None


__all__ = ["should_skip_mutating_logging_config_read", "read_logging_config"]
