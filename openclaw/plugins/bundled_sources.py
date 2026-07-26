"""Resolves bundled plugin source metadata from package manifests.

Bundled candidates are the plugins shipped in the workspace's `extensions/`
directory. The TypeScript original derives them from a full discovery pass that
also covers global/package/bundle roots; that discovery module is not ported
yet, so only the bundled root is scanned here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from openclaw.packages.normalization_core import (
    is_record,
    normalize_optional_string,
)
from openclaw.plugins.loader import DiscoveredPlugin, discover_plugins


@dataclass(frozen=True)
class BundledPluginSource:
    plugin_id: str
    local_path: str
    npm_spec: str | None = None
    version: str | None = None
    config_schema: dict[str, Any] | None = None
    requires_config: bool = False


@dataclass(frozen=True)
class BundledPluginLookup:
    kind: Literal["npmSpec", "pluginId"]
    value: str


def find_bundled_plugin_source_in_map(
    bundled: dict[str, BundledPluginSource],
    lookup: BundledPluginLookup,
) -> BundledPluginSource | None:
    target_value = lookup.value.strip()
    if not target_value:
        return None
    if lookup.kind == "pluginId":
        return bundled.get(target_value)
    for source in bundled.values():
        if source.npm_spec == target_value:
            return source
    return None


def _read_package_json(root: Path) -> dict[str, Any]:
    package_path = root / "package.json"
    if not package_path.is_file():
        return {}
    try:
        raw = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _plugin_config_schema_has_required_fields(schema: Any) -> bool:
    if not is_record(schema):
        return False
    required = schema.get("required")
    return isinstance(required, list) and any(isinstance(entry, str) for entry in required)


def resolve_bundled_plugin_sources(
    workspace_dir: str | Path | None = None,
    discovery: list[DiscoveredPlugin] | None = None,
) -> dict[str, BundledPluginSource]:
    root = Path(workspace_dir) if workspace_dir is not None else Path.cwd()
    candidates = discovery if discovery is not None else discover_plugins(root / "extensions")

    bundled: dict[str, BundledPluginSource] = {}
    for candidate in candidates:
        plugin_id = candidate.manifest.id
        if plugin_id in bundled:
            continue

        package = _read_package_json(Path(candidate.root))
        install = package.get("install")
        npm_spec = (
            normalize_optional_string(install.get("npmSpec") if is_record(install) else None)
            or normalize_optional_string(package.get("name"))
            or None
        )
        version = (
            normalize_optional_string(package.get("version"))
            or normalize_optional_string(candidate.manifest.version)
            or None
        )
        config_schema = candidate.manifest.config_schema

        bundled[plugin_id] = BundledPluginSource(
            plugin_id=plugin_id,
            local_path=candidate.root,
            npm_spec=npm_spec,
            version=version,
            config_schema=config_schema if is_record(config_schema) else None,
            requires_config=_plugin_config_schema_has_required_fields(config_schema),
        )

    return bundled


def find_bundled_plugin_source(
    lookup: BundledPluginLookup,
    workspace_dir: str | Path | None = None,
) -> BundledPluginSource | None:
    bundled = resolve_bundled_plugin_sources(workspace_dir=workspace_dir)
    return find_bundled_plugin_source_in_map(bundled, lookup)


def resolve_bundled_plugin_install_command_hint(
    plugin_id: str,
    workspace_dir: str | Path | None = None,
) -> str | None:
    bundled_source = find_bundled_plugin_source(
        BundledPluginLookup(kind="pluginId", value=plugin_id),
        workspace_dir=workspace_dir,
    )
    if bundled_source is None or not bundled_source.local_path:
        return None
    return f"openclaw plugins install {bundled_source.local_path}"
