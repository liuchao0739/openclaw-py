"""Media temp file helpers create and clean up temporary media files.

Mirrors src/media/temp-files.ts.
"""

from __future__ import annotations

import os


async def unlink_if_exists(file_path: str | None) -> None:
    """Best-effort temp-file cleanup helper for optional paths from media conversion flows."""
    if not file_path:
        return
    try:
        os.unlink(file_path)
    except Exception:
        pass
