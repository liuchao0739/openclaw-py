"""Resolves Claude CLI project storage directories for OpenClaw workspaces."""

from __future__ import annotations

import os
import re
from pathlib import Path

CLAUDE_PROJECTS_DIRNAME = os.path.join(".claude", "projects")
MAX_SANITIZED_PROJECT_LENGTH = 200


def _simple_hash36(input_str: str) -> str:
    hash_val = 0
    for char in input_str:
        hash_val = (hash_val * 31 + ord(char)) & 0xFFFFFFFF
    return format(hash_val, "x")  # base-36 like JS toString(36) for unsigned 32-bit


def sanitize_claude_cli_project_key(workspace_dir: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]", "-", workspace_dir)
    if len(sanitized) <= MAX_SANITIZED_PROJECT_LENGTH:
        return sanitized
    return f"{sanitized[:MAX_SANITIZED_PROJECT_LENGTH]}-{_simple_hash36(workspace_dir)}"


def _canonicalize_workspace_dir(workspace_dir: str) -> str:
    resolved = Path(workspace_dir).resolve()
    try:
        return str(resolved.resolve(strict=False))
    except OSError:
        return str(resolved)


def resolve_claude_cli_project_dir_for_workspace(
    *,
    workspace_dir: str,
    home_dir: str | None = None,
) -> str:
    home = (home_dir or os.environ.get("HOME") or str(Path.home())).strip()
    canonical = _canonicalize_workspace_dir(workspace_dir)
    return os.path.join(
        home,
        CLAUDE_PROJECTS_DIRNAME,
        sanitize_claude_cli_project_key(canonical),
    )