"""Tests for the diffs-language-pack extension entry and API barrel."""

from __future__ import annotations

from pathlib import Path

import pytest

from openclaw_extensions.diffs_language_pack import api, index
from openclaw_extensions.diffs_language_pack.src import plugin, viewer_assets


def test_api_reexports_plugin_entry_contract() -> None:
    assert api.define_plugin_entry is not None
    assert api.OpenClawPluginApi is not None
    assert api.OpenClawPluginHttpRouteHandler is not None
    assert api.PluginLogger is not None


def test_index_default_entry_metadata() -> None:
    entry = index.default
    assert entry.id == "diffs-language-pack"
    assert entry.name == "Diff Viewer Language Pack"
    assert "syntax highlighting" in entry.description
    assert callable(entry.register)
    assert entry.config_schema is not None


def test_register_diffs_language_pack_plugin_registers_route() -> None:
    routes: list[dict[str, object]] = []

    class FakeApi:
        def register_http_route(self, params: dict[str, object]) -> None:
            routes.append(params)

    plugin.register_diffs_language_pack_plugin(FakeApi())
    assert len(routes) == 1
    assert routes[0]["path"] == "/plugins/diffs-language-pack"
    assert routes[0]["auth"] == "plugin"
    assert routes[0]["match"] == "prefix"
    assert callable(routes[0]["handler"])


@pytest.mark.asyncio
async def test_get_served_viewer_asset_returns_loader_and_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    runtime_path = assets_dir / "viewer-runtime.js"
    runtime_path.write_text("console.log('runtime');", encoding="utf-8")

    monkeypatch.setattr(
        viewer_assets,
        "resolve_viewer_runtime_file_path",
        lambda: runtime_path,
    )
    viewer_assets._runtime_asset_cache = None

    loader = await viewer_assets.get_served_viewer_asset(viewer_assets.VIEWER_LOADER_PATH)
    runtime = await viewer_assets.get_served_viewer_asset(viewer_assets.VIEWER_RUNTIME_PATH)

    assert loader is not None
    assert runtime is not None
    assert loader.content_type == "text/javascript; charset=utf-8"
    assert runtime.content_type == "text/javascript; charset=utf-8"
    assert 'import "./viewer-runtime.js?v=' in loader.body
    assert runtime.body == b"console.log('runtime');"
