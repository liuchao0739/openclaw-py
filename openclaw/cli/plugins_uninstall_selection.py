from __future__ import annotations

from typing import Any


def resolve_uninstall_selection(params: dict) -> list[str]:
    return params.get("names", [])


def validate_uninstall_selection(names: list[str]) -> bool:
    return all(isinstance(n, str) and n for n in names)
