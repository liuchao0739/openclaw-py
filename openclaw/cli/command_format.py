from __future__ import annotations


def format_command_path(path: list[str]) -> str:
    return " ".join(path)


def format_command_usage(name: str, args: str = "", options: str = "") -> str:
    parts = [name]
    if args:
        parts.append(args)
    if options:
        parts.append(options)
    return " ".join(parts)
