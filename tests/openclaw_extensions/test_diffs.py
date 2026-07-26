"""Tests for the diffs extension entry and API barrels."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openclaw.plugin_sdk.temp_path import resolve_preferred_openclaw_tmp_dir
from openclaw.plugin_sdk.webhook_ingress import resolve_request_client_ip
from openclaw_extensions.diffs import api, index, runtime_api
from openclaw_extensions.diffs.src import config, plugin

EXTENSION_ROOT = Path(__file__).resolve().parents[2] / "openclaw_extensions" / "diffs"
TS_PACKAGE_JSON = (
    Path(__file__).resolve().parents[2].parent
    / "openclaw-ts"
    / "extensions"
    / "diffs"
    / "package.json"
)


def test_api_reexports_plugin_entry_contract() -> None:
    assert api.define_plugin_entry is not None
    assert api.OpenClawPluginApi is not None
    assert api.PluginLogger is not None
    assert api.AnyAgentTool is not None
    assert api.OpenClawConfig is not None
    assert api.resolve_preferred_openclaw_tmp_dir is resolve_preferred_openclaw_tmp_dir


def test_runtime_api_reexports_request_client_ip() -> None:
    assert runtime_api.resolve_request_client_ip is resolve_request_client_ip


def test_index_default_entry_metadata() -> None:
    entry = index.default
    assert entry.id == "diffs"
    assert entry.name == "Diffs"
    assert "diff viewer" in entry.description.lower()
    assert callable(entry.register)
    assert entry.config_schema is not None
    assert callable(entry.config_schema["safeParse"])


def test_diffs_plugin_config_schema_loads_manifest_schema() -> None:
    manifest = json.loads((EXTENSION_ROOT / "openclaw.plugin.json").read_text(encoding="utf-8"))
    assert config.diffs_plugin_config_schema["jsonSchema"] == manifest["configSchema"]


def test_package_manifest_keeps_runtime_dependencies() -> None:
    if not TS_PACKAGE_JSON.is_file():
        pytest.skip("TypeScript source package.json unavailable")
    package_json = json.loads(TS_PACKAGE_JSON.read_text(encoding="utf-8"))
    assert package_json.get("dependencies", {}).get("@pierre/diffs") is not None


def test_resolve_diffs_language_pack_availability_checks_sibling_runtime(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "diffs"
    root_dir.mkdir()
    language_pack_root = tmp_path / "diffs-language-pack"
    language_pack_root.mkdir()
    (language_pack_root / "openclaw.plugin.json").write_text("{}", encoding="utf-8")
    assets_dir = language_pack_root / "assets"
    assets_dir.mkdir()
    (assets_dir / "viewer-runtime.js").write_text("console.log('runtime');", encoding="utf-8")

    class FakeApi:
        def __init__(self) -> None:
            self.root_dir = str(root_dir)
            self.config: dict[str, object] = {}

    assert plugin.resolve_diffs_language_pack_availability(FakeApi()) is True


def test_register_diffs_plugin_requires_unported_runtime_modules() -> None:
    class FakeApi:
        def __init__(self) -> None:
            self.logger = None
            self.plugin_config: dict[str, object] = {}
            self.config: dict[str, object] = {}

        def register_tool(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("register_tool should not run before runtime modules are ported")

        def register_http_route(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError(
                "register_http_route should not run before runtime modules are ported"
            )

        def on(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("on should not run before runtime modules are ported")

    with pytest.raises(ModuleNotFoundError):
        plugin.register_diffs_plugin(FakeApi())
