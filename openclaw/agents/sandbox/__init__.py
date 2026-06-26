"""Agents sandbox package — hash, browser bridges, test args, stat parse.

Mirrors src/agents/sandbox/.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

# --- Hash ---

def hash_text_sha256(value: str) -> str:
    """Return a stable SHA-256 hex digest for sandbox config/cache keys."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# --- Browser bridges registry ---

_browser_bridges: dict[str, dict[str, Any]] = {}


def get_browser_bridges() -> dict[str, dict[str, Any]]:
    """Return the in-process browser bridge registry."""
    return _browser_bridges


def register_browser_bridge(
    session_key: str,
    bridge: Any,
    container_name: str,
    auth_token: str | None = None,
    auth_password: str | None = None,
) -> None:
    """Register a browser bridge for a sandbox session."""
    _browser_bridges[session_key] = {
        "bridge": bridge,
        "containerName": container_name,
        "authToken": auth_token,
        "authPassword": auth_password,
    }


def unregister_browser_bridge(session_key: str) -> None:
    """Remove a browser bridge."""
    _browser_bridges.pop(session_key, None)


def clear_browser_bridges() -> None:
    """Clear all browser bridges."""
    _browser_bridges.clear()


# --- Docker test args ---

def find_docker_args_call(calls: list[list[Any]], command: str) -> list[str] | None:
    """Find the first mocked Docker call whose argv starts with the requested command."""
    for call in calls:
        if call and isinstance(call[0], list) and call[0] and call[0][0] == command:
            return call[0]
    return None


def collect_docker_flag_values(args: list[str], flag: str) -> list[str]:
    """Collect every value passed after a repeated Docker flag."""
    values: list[str] = []
    for i, arg in enumerate(args):
        if arg == flag and i + 1 < len(args) and isinstance(args[i + 1], str):
            values.append(args[i + 1])
    return values


# --- Stat parsing ---

def _parse_strict_non_negative_int(value: str) -> int | None:
    """Parse a non-negative integer, returning None for values exceeding JS safe integer range."""
    if not value or not value.isdigit():
        return None
    result = int(value)
    if result > 9007199254740991:  # Number.MAX_SAFE_INTEGER
        return None
    return result


def _as_date_timestamp_ms(value: float) -> int | None:
    if value != value:  # NaN check
        return None
    if value == float("inf") or value == float("-inf"):
        return None
    return int(value)


def parse_sandbox_stat_size(value: str | None) -> int:
    """Parse file sizes, capping huge integer strings at the largest safe integer."""
    raw = value or "0"
    parsed = _parse_strict_non_negative_int(raw)
    if parsed is not None:
        return parsed
    if raw.isdigit():
        return 9007199254740991  # Number.MAX_SAFE_INTEGER
    return 0


def parse_sandbox_stat_mtime_ms(value: str | None) -> int:
    """Parse stat mtimes from epoch seconds or date strings into millisecond timestamps."""
    import re

    raw = value or "0"
    if re.match(r"^\d+(?:\.\d+)?$", raw):
        mtime_ms = float(raw) * 1000
        return _as_date_timestamp_ms(mtime_ms) or 0
    try:
        parsed = datetime.fromisoformat(raw).timestamp() * 1000
        return _as_date_timestamp_ms(parsed) or 0
    except (ValueError, TypeError):
        return 0
