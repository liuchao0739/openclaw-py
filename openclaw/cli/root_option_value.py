from __future__ import annotations

from typing import Any


def get_root_option_value(argv: list[str], name: str) -> str | None:
    flag = f"--{name}"
    args = argv[2:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            break
        if arg == flag:
            next_val = args[i + 1] if i + 1 < len(args) else None
            if next_val and not next_val.startswith("-"):
                return next_val
            return None
        if arg.startswith(f"{flag}="):
            return arg[len(flag) + 1 :]
        i += 1
    return None


def has_root_option(argv: list[str], name: str) -> bool:
    flag = f"--{name}"
    return any(arg == flag or arg.startswith(f"{flag}=") for arg in argv[2:])
