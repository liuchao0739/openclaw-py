from __future__ import annotations

import json
import os
from typing import Any

from openclaw.plugins.constants import (
    PLUGIN_CONFIG_FILENAME,
    PLUGIN_MANIFEST_FILENAME,
    LEGACY_PLUGIN_MANIFEST_FILENAME,
)
from openclaw.plugins.compat_types import PluginCompatStatus


def resolve_plugin_workdir() -> str:
    return ".openclaw/plugins"


def resolve_plugin_config_path() -> str:
    return os.path.join(resolve_plugin_workdir(), PLUGIN_CONFIG_FILENAME)


def resolve_plugin_manifest_path(plugin_dir: str) -> str:
    manifest_path = os.path.join(plugin_dir, PLUGIN_MANIFEST_FILENAME)
    if os.path.exists(manifest_path):
        return manifest_path
    legacy_path = os.path.join(plugin_dir, LEGACY_PLUGIN_MANIFEST_FILENAME)
    if os.path.exists(legacy_path):
        return legacy_path
    return manifest_path


def load_plugin_manifest(plugin_dir: str) -> dict[str, Any] | None:
    manifest_path = resolve_plugin_manifest_path(plugin_dir)
    if not os.path.exists(manifest_path):
        return None
    try:
        with open(manifest_path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def validate_plugin_manifest(manifest: dict[str, Any]) -> tuple[bool, str | None]:
    if not manifest.get("name"):
        return False, "Plugin manifest missing 'name' field"
    if not manifest.get("version"):
        return False, "Plugin manifest missing 'version' field"
    return True, None


def list_installed_plugins() -> list[dict[str, Any]]:
    workdir = resolve_plugin_workdir()
    if not os.path.exists(workdir):
        return []
    plugins: list[dict[str, Any]] = []
    for entry in os.listdir(workdir):
        plugin_dir = os.path.join(workdir, entry)
        if not os.path.isdir(plugin_dir):
            continue
        manifest = load_plugin_manifest(plugin_dir)
        if not manifest:
            continue
        plugins.append({
            "name": manifest.get("name", entry),
            "version": manifest.get("version", "0.0.0"),
            "dir": plugin_dir,
            "status": manifest.get("status", PluginCompatStatus.COMPAT),
        })
    return plugins


def load_plugin_config() -> dict[str, Any]:
    config_path = resolve_plugin_config_path()
    if not os.path.exists(config_path):
        return {"plugins": {}}
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"plugins": {}}


def save_plugin_config(config: dict[str, Any]) -> None:
    config_path = resolve_plugin_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
