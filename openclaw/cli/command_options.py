from __future__ import annotations

from typing import Any


def parse_command_options(argv: list[str]) -> dict:
    options: dict[str, Any] = {}
    positionals: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("--"):
            if "=" in arg:
                key, _, value = arg[2:].partition("=")
                options[key] = value
            else:
                key = arg[2:]
                next_val = argv[i + 1] if i + 1 < len(argv) else None
                if next_val and not next_val.startswith("-"):
                    options[key] = next_val
                    i += 1
                else:
                    options[key] = True
        elif arg.startswith("-") and len(arg) > 1:
            options[arg[1:]] = True
        else:
            positionals.append(arg)
        i += 1
    return {"options": options, "positionals": positionals}
