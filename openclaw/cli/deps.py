from __future__ import annotations

from typing import Any


def resolve_deps(params: dict) -> dict:
    return {}


def check_deps(params: dict) -> list[str]:
    return []


def format_deps_error(missing: list[str]) -> str:
    return f"Missing dependencies: {", ".join(missing)}"
