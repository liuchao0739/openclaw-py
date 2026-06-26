"""Transcript headers record session identity and version as the first JSONL entry."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from openclaw.config.sessions.version import CURRENT_SESSION_VERSION


def create_session_transcript_header(
    session_id: str | None = None,
    cwd: str | None = None,
) -> dict[str, Any]:
    """Create a session transcript header entry with current version metadata."""
    return {
        "type": "session",
        "version": CURRENT_SESSION_VERSION,
        "id": session_id or str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cwd": cwd or os.getcwd(),
    }
