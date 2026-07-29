from __future__ import annotations

from typing import Any


def resolve_daemon_cli_compat(argv: list[str]) -> list[str]:
    return argv


def is_daemon_cli_compat_mode(argv: list[str]) -> bool:
    return "--compat" in argv
