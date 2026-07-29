from __future__ import annotations

from typing import Any


def should_register_command(name: str, context: Any = None) -> bool:
    return True


def validate_command_registration(name: str, spec: Any) -> None:
    pass
