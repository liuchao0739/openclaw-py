from __future__ import annotations

import sys
from typing import Any


def is_windows() -> bool:
    return sys.platform in ("win32", "cygwin")


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def normalize_windows_argv(argv: list[str]) -> list[str]:
    if not is_windows():
        return argv
    normalized: list[str] = []
    for arg in argv:
        if arg.startswith('"') and arg.endswith('"'):
            normalized.append(arg[1:-1])
        else:
            normalized.append(arg)
    return normalized


def should_quote_argv(argv: list[str]) -> bool:
    return is_windows()
