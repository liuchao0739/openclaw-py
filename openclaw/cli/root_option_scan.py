from __future__ import annotations

from typing import Any


def scan_root_options(argv: list[str]) -> dict:
    options: dict[str, Any] = {}
    args = argv[2:]
    i = 0
    while i < len(args):
        arg = args[i]
        if not arg or arg == "--":
            break
        if arg.startswith("--"):
            if "=" in arg:
                key, _, value = arg[2:].partition("=")
                options[key] = value
            else:
                key = arg[2:]
                next_val = args[i + 1] if i + 1 < len(args) else None
                if next_val and not next_val.startswith("-"):
                    options[key] = next_val
                    i += 1
                else:
                    options[key] = True
        elif arg.startswith("-") and len(arg) > 1:
            options[arg[1:]] = True
        else:
            break
        i += 1
    return options
