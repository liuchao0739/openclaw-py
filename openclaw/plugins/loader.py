"""Plugin discovery and loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openclaw.plugin_sdk import PLUGIN_MANIFEST_FILENAME
from openclaw.plugin_sdk.manifest import PluginManifest, load_plugin_manifest


@dataclass
class DiscoveredPlugin:
    id: str
    root: str
    manifest: PluginManifest


def discover_plugins(extensions_dir: str | Path) -> list[DiscoveredPlugin]:
    root = Path(extensions_dir)
    if not root.is_dir():
        return []

    discovered: list[DiscoveredPlugin] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        manifest_path = child / PLUGIN_MANIFEST_FILENAME
        if not manifest_path.exists():
            continue
        manifest = load_plugin_manifest(manifest_path)
        discovered.append(DiscoveredPlugin(id=manifest.id, root=str(child), manifest=manifest))
    return discovered
