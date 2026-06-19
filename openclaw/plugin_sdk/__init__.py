"""Plugin SDK public API."""

from __future__ import annotations

PLUGIN_MANIFEST_FILENAME = "openclaw.plugin.json"


def plugin_manifest_path(root: str) -> str:
    from pathlib import Path

    return str(Path(root) / PLUGIN_MANIFEST_FILENAME)
