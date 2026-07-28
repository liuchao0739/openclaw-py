"""Import specifier helpers for safe import path conversion."""

from __future__ import annotations

import os
import platform


def to_safe_import_path(specifier: str) -> str:
    if platform.system() != "Windows":
        return specifier
    if specifier.startswith("file://"):
        return specifier
    if os.path.isabs(specifier):
        from urllib.request import pathname2url
        return f"file://{pathname2url(specifier)}"
    return specifier
