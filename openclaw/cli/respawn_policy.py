from __future__ import annotations

from typing import Any


def should_respawn(argv: list[str]) -> bool:
    return False


def resolve_respawn_policy(params: dict) -> dict:
    return {"respawn": False}


def build_respawn_argv(argv: list[str]) -> list[str]:
    return list(argv)
