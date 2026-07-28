from __future__ import annotations

from typing import Any


def parse_cli_arguments(argv: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "command": "",
        "args": [],
        "flags": {},
    }
    if not argv:
        return result
    result["command"] = argv[0]
    for arg in argv[1:]:
        if arg.startswith("--"):
            key = arg[2:]
            if "=" in key:
                k, v = key.split("=", 1)
                result["flags"][k] = v
            else:
                result["flags"][key] = True
        elif arg.startswith("-"):
            key = arg[1:]
            result["flags"][key] = True
        else:
            result["args"].append(arg)
    return result
