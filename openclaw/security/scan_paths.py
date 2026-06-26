"""Path containment helpers re-exported for security scanners.

Mirrors src/security/scan-paths.ts.
"""

from __future__ import annotations

import re


def extension_uses_skipped_scanner_path(entry: str) -> bool:
    """Return True for extension paths intentionally skipped by source scanners."""
    segments = [s for s in re.split(r"[\\/]+", entry) if s]
    return any(
        segment == "node_modules"
        or (segment.startswith(".") and segment not in (".", ".."))
        for segment in segments
    )
