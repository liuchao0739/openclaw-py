"""Resolves archive paths through safe filesystem defaults.

Mirrors src/infra/archive-path.ts. Self-contained port with is_windows_drive_path.
"""

from __future__ import annotations

import re

_WINDOWS_DRIVE_RE = re.compile(r"^[a-zA-Z]:[\\/]")


def is_windows_drive_path(path: str) -> bool:
    """Check if a path starts with a Windows drive letter (e.g. C:\\)."""
    if not isinstance(path, str):
        return False
    return bool(_WINDOWS_DRIVE_RE.match(path))
