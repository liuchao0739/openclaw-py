from __future__ import annotations

from typing import Any


def is_setup_onboard_configure_command(argv: list[str]) -> bool:
    args = argv[2:]
    if not args:
        return False
    return args[0] in ("setup", "onboard", "configure")


def resolve_fast_path_help(argv: list[str]) -> str | None:
    if is_setup_onboard_configure_command(argv):
        return None
    return None
