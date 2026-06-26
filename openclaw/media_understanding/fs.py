"""Small file-system helpers for optional media attachment paths.

Mirrors src/media-understanding/fs.ts.
"""

from __future__ import annotations

import os


async def file_exists(file_path: str | None) -> bool:
    """Safely check optional media file paths without throwing on empty input."""
    if not file_path:
        return False
    return os.path.exists(file_path)
