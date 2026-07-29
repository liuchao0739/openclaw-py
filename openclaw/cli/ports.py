from __future__ import annotations

from typing import Any

MAX_TCP_PORT = 65535


def parse_tcp_port(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    try:
        port = int(raw)
    except (ValueError, TypeError):
        return None
    if 1 <= port <= MAX_TCP_PORT:
        return port
    return None


def parse_port(raw: Any) -> int | None:
    return parse_tcp_port(raw)


def is_valid_port(value: Any) -> bool:
    return parse_tcp_port(value) is not None
