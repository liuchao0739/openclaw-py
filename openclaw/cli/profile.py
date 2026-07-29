from __future__ import annotations

import os
from typing import Any

from openclaw.packages.normalization_core import normalize_optional_string


def resolve_profile(argv: list[str]) -> str | None:
    args = argv[2:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--profile":
            next_val = args[i + 1] if i + 1 < len(args) else None
            return normalize_optional_string(next_val)
        if arg.startswith("--profile="):
            return normalize_optional_string(arg[len("--profile=") :])
        i += 1
    return normalize_optional_string(os.environ.get("OPENCLAW_PROFILE"))


def has_profile_flag(argv: list[str]) -> bool:
    args = argv[2:]
    return any(arg == "--profile" or arg.startswith("--profile=") for arg in args)
