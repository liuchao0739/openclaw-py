from __future__ import annotations

import re

from openclaw.packages.normalization_core import normalize_optional_string

_NO_COLOR_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return _NO_COLOR_RE.sub("", text)


def has_no_color_flag(argv: list[str]) -> bool:
    return "--no-color" in argv


def should_use_color(argv: list[str] | None = None, env: dict | None = None) -> bool:
    import os
    import sys

    if argv and has_no_color_flag(argv):
        return False
    env_map = env if env is not None else dict(os.environ)
    if env_map.get("NO_COLOR"):
        return False
    if env_map.get("FORCE_COLOR") == "0":
        return False
    return sys.stdout.isatty()
