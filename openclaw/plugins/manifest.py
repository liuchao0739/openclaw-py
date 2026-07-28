from __future__ import annotations

import json
import os
from typing import Any


def resolve_plugin_manifest_path_from_dir(plugin_dir: str) -> str | None:
    candidates = [
        os.path.join(plugin_dir, "openclaw.plugin.json"),
        os.path.join(plugin_dir, "plugin.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def load_manifest(plugin_dir: str) -> dict[str, Any] | None:
    manifest_path = resolve_plugin_manifest_path_from_dir(plugin_dir)
    if not manifest_path:
        return None
    try:
        with open(manifest_path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not manifest.get("name"):
        errors.append("Missing 'name' field")
    if not manifest.get("version"):
        errors.append("Missing 'version' field")
    if manifest.get("version") and not isinstance(manifest["version"], str):
        errors.append("'version' must be a string")
    return errors


def get_manifest_entry(manifest: dict[str, Any]) -> str | None:
    return manifest.get("entry")
