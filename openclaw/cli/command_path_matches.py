from __future__ import annotations


def command_path_matches(path: list[str], target: list[str]) -> bool:
    if len(path) < len(target):
        return False
    return path[: len(target)] == target


def command_path_starts_with(path: list[str], prefix: list[str]) -> bool:
    return command_path_matches(path, prefix)
