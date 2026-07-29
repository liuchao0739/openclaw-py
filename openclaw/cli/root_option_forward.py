from __future__ import annotations

from typing import Any


def forward_root_options(argv: list[str], target: list[str]) -> list[str]:
    root_opts: list[str] = []
    args = argv[2:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            break
        if arg.startswith("-"):
            root_opts.append(arg)
            if not arg.startswith("--") or "=" not in arg:
                next_val = args[i + 1] if i + 1 < len(args) else None
                if next_val and not next_val.startswith("-"):
                    root_opts.append(next_val)
                    i += 1
        else:
            break
        i += 1
    return [*root_opts, *target]
