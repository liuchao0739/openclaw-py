from __future__ import annotations

from typing import Any


def parse_gateway_run_argv(argv: list[str]) -> dict:
    options: dict[str, Any] = {"args": []}
    args = argv[2:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--port":
            next_val = args[i + 1] if i + 1 < len(args) else None
            if next_val:
                options["port"] = next_val
                i += 1
        elif arg.startswith("--port="):
            options["port"] = arg[len("--port=") :]
        elif arg == "--host":
            next_val = args[i + 1] if i + 1 < len(args) else None
            if next_val:
                options["host"] = next_val
                i += 1
        elif arg.startswith("--host="):
            options["host"] = arg[len("--host=") :]
        else:
            options["args"].append(arg)
        i += 1
    return options
