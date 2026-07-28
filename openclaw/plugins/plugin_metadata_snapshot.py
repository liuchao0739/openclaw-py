from __future__ import annotations

from typing import Any


def build_plugin_metadata_snapshot(
    plugin_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": plugin_id,
        "name": manifest.get("name", plugin_id),
        "version": manifest.get("version", "0.0.0"),
        "description": manifest.get("description", ""),
        "entry": manifest.get("entry"),
        "timestamp": __import__("time").time(),
    }
