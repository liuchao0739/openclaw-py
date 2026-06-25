"""Agent path formatting helpers.

Canonicalizes local paths and formats paths relative to a workspace when possible.
"""

from __future__ import annotations

import os


def canonicalize_path(path: str) -> str:
    """Resolve a path to its canonical (real) form, following symlinks.

    Falls back to the raw path if resolution fails.
    """
    try:
        return os.path.realpath(path)
    except Exception:
        return path


def is_local_path(value: str) -> bool:
    """Return True if the value is NOT a package source or URL protocol."""
    trimmed = value.strip()
    non_local_prefixes = ("npm:", "git:", "github:", "http:", "https:", "ssh:")
    return not any(trimmed.startswith(prefix) for prefix in non_local_prefixes)


def _resolve_against_cwd(file_path: str, cwd: str) -> str:
    if os.path.isabs(file_path):
        return os.path.abspath(file_path)
    return os.path.abspath(os.path.join(cwd, file_path))


def _get_cwd_relative_path(file_path: str, cwd: str) -> str | None:
    resolved_cwd = os.path.abspath(cwd)
    resolved_path = _resolve_against_cwd(file_path, resolved_cwd)
    relative_path = os.path.relpath(resolved_path, resolved_cwd)

    is_inside_cwd = (
        relative_path == ""
        or (
            relative_path != ".."
            and not relative_path.startswith(".." + os.sep)
            and not os.path.isabs(relative_path)
        )
    )

    if is_inside_cwd:
        return relative_path or "."
    return None


def format_path_relative_to_cwd_or_absolute(file_path: str, cwd: str) -> str:
    """Format a path relative to cwd, or as an absolute path if outside cwd."""
    absolute_path = _resolve_against_cwd(file_path, cwd)
    relative = _get_cwd_relative_path(absolute_path, cwd)
    result = relative if relative is not None else absolute_path
    return result.replace(os.sep, "/")
