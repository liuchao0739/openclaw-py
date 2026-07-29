from __future__ import annotations

from typing import Any

COMMAND_CATALOG: dict[str, Any] = {}


def register_command_in_catalog(name: str, spec: Any) -> None:
    COMMAND_CATALOG[name] = spec


def get_command_from_catalog(name: str) -> Any:
    return COMMAND_CATALOG.get(name)


def list_catalog_commands() -> list[str]:
    return list(COMMAND_CATALOG.keys())
