from __future__ import annotations

from typing import Any

PRECOMPUTED_HELP: dict[str, str] = {}


def get_precomputed_help(command: str) -> str | None:
    return PRECOMPUTED_HELP.get(command)


def set_precomputed_help(command: str, text: str) -> None:
    PRECOMPUTED_HELP[command] = text


def has_precomputed_help(command: str) -> bool:
    return command in PRECOMPUTED_HELP
