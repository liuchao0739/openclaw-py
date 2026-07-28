from __future__ import annotations

from typing import Any


def load_plugins(
    plugin_dirs: list[str] | None = None,
    options: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    plugin_dirs = plugin_dirs or [".openclaw/plugins"]
    options = options or {}
    results: list[dict[str, Any]] = []

    for plugin_dir in plugin_dirs:
        if not os.path.isdir(plugin_dir):
            continue
        import os
        for entry in os.listdir(plugin_dir):
            full_path = os.path.join(plugin_dir, entry)
            if not os.path.isdir(full_path):
                continue
            from openclaw.plugins.manifest import load_manifest
            manifest = load_manifest(full_path)
            if not manifest:
                continue
            results.append({
                "id": entry,
                "manifest": manifest,
                "dir": full_path,
            })

    return results


def scan_plugins(
    plugin_dir: str = ".openclaw/plugins",
) -> list[dict[str, Any]]:
    return load_plugins([plugin_dir])
