"""Secret-file reader for ACP command-line credentials.

Mirrors src/acp/secret-file.ts.
"""

from __future__ import annotations

import os
from pathlib import Path

MAX_SECRET_FILE_BYTES = 64 * 1024


def read_secret_from_file(file_path: str, label: str) -> str:
    """Read an ACP secret file with size and symlink policy."""
    p = Path(file_path)
    if p.is_symlink():
        raise ValueError(f"{label}: symlink secret files are not allowed")
    if not p.is_file():
        raise FileNotFoundError(f"{label}: secret file not found: {file_path}")
    size = p.stat().st_size
    if size > MAX_SECRET_FILE_BYTES:
        raise ValueError(f"{label}: secret file too large ({size} > {MAX_SECRET_FILE_BYTES})")
    return p.read_text(encoding="utf-8").strip()
