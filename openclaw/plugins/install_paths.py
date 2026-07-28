from __future__ import annotations

import json
import os
from typing import Any


def resolve_plugin_install_path(
    plugin_id: str,
    base_dir: str | None = None,
) -> str:
    base = base_dir or ".openclaw/plugins"
    safe_id = plugin_id.replace("/", "_").replace("@", "")
    return os.path.join(base, safe_id)


def resolve_plugin_source_path(
    plugin_id: str,
    source: str = "bundled",
) -> str | None:
    if source == "bundled":
        return None
    return None


def create_plugin_install_paths(
    plugin_id: str,
    base_dir: str | None = None,
) -> dict[str, str]:
    install_dir = resolve_plugin_install_path(plugin_id, base_dir)
    return {
        "installDir": install_dir,
        "manifestPath": os.path.join(install_dir, "openclaw.plugin.json"),
        "configPath": os.path.join(install_dir, "config.json"),
    }
