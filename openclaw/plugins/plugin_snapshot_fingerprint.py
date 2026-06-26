"""Plugin snapshot fingerprint helpers.

Mirrors src/plugins/plugin-snapshot-fingerprint.ts.
"""

from __future__ import annotations

import os
from typing import Any


def file_fingerprint(file_path: str) -> list[Any]:
    """Return a fingerprint tuple for a file path.

    Returns [path, kind, size, mtime_ns, ctime_ns] for existing files,
    or [path, "missing"] for non-existent paths.
    """
    try:
        stat = os.stat(file_path)
        kind = "file" if os.path.isfile(file_path) else ("dir" if os.path.isdir(file_path) else "other")
        return [file_path, kind, str(stat.st_size), str(stat.st_mtime_ns), str(stat.st_ctime_ns)]
    except OSError:
        return [file_path, "missing"]
