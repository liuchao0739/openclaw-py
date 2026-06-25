"""Missing session cwd detection.

Helps resume flows decide whether to stop, prompt, or continue in the current process cwd.
"""

from __future__ import annotations

import os
from typing import TypedDict


class SessionCwdIssue(TypedDict, total=False):
    sessionFile: str | None
    sessionCwd: str
    fallbackCwd: str


class SessionCwdSource(TypedDict, total=False):
    getCwd: Any
    getSessionFile: Any


def detect_missing_session_cwd(
    source: dict[str, Any],
    fallback_cwd: str,
) -> SessionCwdIssue | None:
    """Detect if the session cwd is missing or invalid."""
    get_cwd = source.get("getCwd")
    get_session_file = source.get("getSessionFile")
    session_cwd = get_cwd() if callable(get_cwd) else ""
    session_file = get_session_file() if callable(get_session_file) else None

    if not session_cwd or not os.path.isdir(session_cwd):
        return SessionCwdIssue(
            sessionFile=session_file,
            sessionCwd=session_cwd or "",
            fallbackCwd=fallback_cwd,
        )
    return None
