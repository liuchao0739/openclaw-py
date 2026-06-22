"""POSIX container path helpers for sandbox paths."""

from __future__ import annotations

import posixpath


def normalize_container_path(value: str) -> str:
    normalized = posixpath.normpath(value)
    return "/" if normalized == "." else normalized


def is_path_inside_container_root(root: str, target: str) -> bool:
    normalized_root = normalize_container_path(root)
    normalized_target = normalize_container_path(target)
    if normalized_root == "/":
        return True
    return normalized_target == normalized_root or normalized_target.startswith(
        f"{normalized_root}/"
    )


def relative_path_escapes_container_root(relative_path: str) -> bool:
    return (
        relative_path == ".."
        or relative_path.startswith("../")
        or posixpath.isabs(relative_path)
    )