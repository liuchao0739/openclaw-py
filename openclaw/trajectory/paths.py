"""Trajectory path helpers resolve storage paths for trajectory artifacts.

Mirrors src/trajectory/paths.ts.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Mapping

TRAJECTORY_RUNTIME_CAPTURE_MAX_BYTES = 10 * 1024 * 1024
TRAJECTORY_RUNTIME_FILE_MAX_BYTES = 50 * 1024 * 1024
TRAJECTORY_RUNTIME_EVENT_MAX_BYTES = 256 * 1024


def safe_trajectory_session_file_name(session_id: str) -> str:
    """Scrub a session ID for filesystem safety."""
    if not isinstance(session_id, str):
        return "session"
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)[:120]
    return safe if re.search(r"[A-Za-z0-9]", safe) else "session"


def _resolve_home_relative_path(path: str) -> str:
    """Resolve a path that may start with ~."""
    if path.startswith("~"):
        return os.path.expanduser(path)
    return path


def _is_path_inside(base: str, target: str) -> bool:
    """Check if target path is inside base path."""
    try:
        base_resolved = str(Path(base).resolve())
        target_resolved = str(Path(target).resolve())
        return target_resolved.startswith(base_resolved + os.sep) or target_resolved == base_resolved
    except Exception:
        return False


def _resolve_contained_path(base_dir: str, file_name: str) -> str:
    """Resolve a path contained within base_dir, throwing if it escapes."""
    resolved_base = str(Path(base_dir).resolve())
    resolved_file = str(Path(resolved_base, file_name).resolve())
    if resolved_file == resolved_base or not _is_path_inside(resolved_base, resolved_file):
        raise OSError("Trajectory file path escaped its configured directory")
    return resolved_file


def resolve_trajectory_file_path(
    params: Mapping[str, str] | None = None,
) -> str:
    """Resolve the trajectory file path for a session."""
    params = params or {}
    env = params.get("env") or os.environ
    if isinstance(env, Mapping):
        dir_override = (env.get("OPENCLAW_TRAJECTORY_DIR") or "").strip()
    else:
        dir_override = ""

    session_id = params.get("sessionId", "")
    session_file = params.get("sessionFile")

    if dir_override:
        return _resolve_contained_path(
            _resolve_home_relative_path(dir_override),
            f"{safe_trajectory_session_file_name(session_id)}.jsonl",
        )
    if not session_file:
        return str(Path(os.getcwd()) / f"{safe_trajectory_session_file_name(session_id)}.trajectory.jsonl")
    if session_file.endswith(".jsonl"):
        return f"{session_file[:-len('.jsonl')]}.trajectory.jsonl"
    return f"{session_file}.trajectory.jsonl"


def resolve_trajectory_pointer_file_path(session_file: str) -> str:
    """Resolve the trajectory pointer file path for a session file."""
    if session_file.endswith(".jsonl"):
        return f"{session_file[:-len('.jsonl')]}.trajectory-path.json"
    return f"{session_file}.trajectory-path.json"
