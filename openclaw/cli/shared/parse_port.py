"""CLI-facing TCP port parser wrapper."""

from __future__ import annotations

from typing import Any

MAX_TCP_PORT = 65535


def parse_tcp_port(raw: Any) -> int | None:
    """Parse a TCP port from unknown input, returning None for invalid values."""
    if raw is None:
        return None
    try:
        if isinstance(raw, bool):
            return None
        port = int(raw)
    except (ValueError, TypeError):
        return None
    if 1 <= port <= MAX_TCP_PORT:
        return port
    return None


def parse_port(raw: Any) -> int | None:
    """Parse a TCP port from CLI/config input, returning None for invalid values."""
    return parse_tcp_port(raw)
