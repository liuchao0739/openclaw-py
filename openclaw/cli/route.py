from __future__ import annotations

from typing import Any


def resolve_route(argv: list[str]) -> dict:
    return {"command": [], "args": [], "options": {}}


def route_matches(path: list[str], pattern: list[str]) -> bool:
    if len(path) < len(pattern):
        return False
    return path[: len(pattern)] == pattern
