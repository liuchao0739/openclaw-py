"""Tests bundled plugin source resolution from package manifests."""

from __future__ import annotations

import json
from pathlib import Path

from openclaw.plugin_sdk import PLUGIN_MANIFEST_FILENAME
from openclaw.plugins.bundled_sources import (
    BundledPluginLookup,
    find_bundled_plugin_source_in_map,
    resolve_bundled_plugin_install_command_hint,
    resolve_bundled_plugin_sources,
)


def write_plugin(
    workspace: Path,
    plugin_id: str,
    *,
    package: dict | None = None,
    manifest_extra: dict | None = None,
) -> Path:
    root = workspace / "extensions" / plugin_id
    root.mkdir(parents=True)
    (root / PLUGIN_MANIFEST_FILENAME).write_text(
        json.dumps({"id": plugin_id, **(manifest_extra or {})}), encoding="utf-8"
    )
    if package is not None:
        (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    return root


def test_resolves_bundled_sources_with_package_metadata(tmp_path: Path) -> None:
    write_plugin(
        tmp_path,
        "acpx",
        package={"name": "@openclaw/acpx", "version": "1.2.3"},
    )

    bundled = resolve_bundled_plugin_sources(workspace_dir=tmp_path)

    source = bundled["acpx"]
    assert source.plugin_id == "acpx"
    assert source.local_path == str(tmp_path / "extensions" / "acpx")
    assert source.npm_spec == "@openclaw/acpx"
    assert source.version == "1.2.3"
    assert source.requires_config is False


def test_explicit_npm_spec_wins_over_package_name(tmp_path: Path) -> None:
    write_plugin(
        tmp_path,
        "acpx",
        package={"name": "@openclaw/acpx", "install": {"npmSpec": "acpx@next"}},
    )

    bundled = resolve_bundled_plugin_sources(workspace_dir=tmp_path)
    assert bundled["acpx"].npm_spec == "acpx@next"


def test_falls_back_to_manifest_version(tmp_path: Path) -> None:
    write_plugin(tmp_path, "acpx", manifest_extra={"version": "0.9.0"})

    bundled = resolve_bundled_plugin_sources(workspace_dir=tmp_path)
    assert bundled["acpx"].version == "0.9.0"


def test_requires_config_when_schema_lists_required_fields(tmp_path: Path) -> None:
    write_plugin(
        tmp_path,
        "acpx",
        manifest_extra={"configSchema": {"required": ["token"]}},
    )

    bundled = resolve_bundled_plugin_sources(workspace_dir=tmp_path)
    source = bundled["acpx"]
    assert source.requires_config is True
    assert source.config_schema == {"required": ["token"]}


def test_requires_config_ignores_non_string_required_entries(tmp_path: Path) -> None:
    write_plugin(tmp_path, "acpx", manifest_extra={"configSchema": {"required": [1, 2]}})

    bundled = resolve_bundled_plugin_sources(workspace_dir=tmp_path)
    assert bundled["acpx"].requires_config is False


def test_lookup_by_plugin_id_and_npm_spec(tmp_path: Path) -> None:
    write_plugin(tmp_path, "acpx", package={"name": "@openclaw/acpx"})
    bundled = resolve_bundled_plugin_sources(workspace_dir=tmp_path)

    by_id = find_bundled_plugin_source_in_map(
        bundled, BundledPluginLookup(kind="pluginId", value="acpx")
    )
    by_spec = find_bundled_plugin_source_in_map(
        bundled, BundledPluginLookup(kind="npmSpec", value="@openclaw/acpx")
    )
    assert by_id is not None
    assert by_spec == by_id


def test_lookup_returns_none_for_blank_or_unknown_value(tmp_path: Path) -> None:
    write_plugin(tmp_path, "acpx")
    bundled = resolve_bundled_plugin_sources(workspace_dir=tmp_path)

    assert (
        find_bundled_plugin_source_in_map(
            bundled, BundledPluginLookup(kind="pluginId", value="   ")
        )
        is None
    )
    assert (
        find_bundled_plugin_source_in_map(
            bundled, BundledPluginLookup(kind="npmSpec", value="missing")
        )
        is None
    )


def test_install_command_hint_points_at_local_path(tmp_path: Path) -> None:
    root = write_plugin(tmp_path, "acpx")

    hint = resolve_bundled_plugin_install_command_hint("acpx", workspace_dir=tmp_path)
    assert hint == f"openclaw plugins install {root}"


def test_install_command_hint_is_none_for_unknown_plugin(tmp_path: Path) -> None:
    assert resolve_bundled_plugin_install_command_hint("acpx", workspace_dir=tmp_path) is None


def test_malformed_package_json_is_ignored(tmp_path: Path) -> None:
    root = write_plugin(tmp_path, "acpx")
    (root / "package.json").write_text("{ not json", encoding="utf-8")

    bundled = resolve_bundled_plugin_sources(workspace_dir=tmp_path)
    assert bundled["acpx"].npm_spec is None
