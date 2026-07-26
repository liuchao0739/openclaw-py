"""Tests for the bonjour extension entry and package manifest."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

EXTENSION_ROOT = Path(__file__).resolve().parents[2] / "openclaw_extensions" / "bonjour"
TS_EXTENSION_ROOT = (
    Path(__file__).resolve().parents[2].parent / "openclaw-ts" / "extensions" / "bonjour"
)
TS_ROOT_PACKAGE_JSON = Path(__file__).resolve().parents[2].parent / "openclaw-ts" / "package.json"


@pytest.mark.asyncio
async def test_lazy_loads_advertiser_runtime_when_gateway_discovery_advertises() -> None:
    advertiser_module_loaded = MagicMock()
    runtime_module_loaded = MagicMock()
    stop = MagicMock()
    start_gateway_bonjour_advertiser = AsyncMock(return_value={"stop": stop})
    register_uncaught_exception_handler = MagicMock()
    register_unhandled_rejection_handler = MagicMock()
    discovery_service: dict[str, Any] | None = None
    logger = SimpleNamespace(
        info=MagicMock(),
        warn=MagicMock(),
        error=MagicMock(),
        debug=MagicMock(),
    )

    class FakeApi:
        def __init__(self) -> None:
            self.logger = logger

        def register_gateway_discovery_service(self, service: dict[str, Any]) -> None:
            nonlocal discovery_service
            discovery_service = service

    original_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None) -> Any:
        if name == "openclaw_extensions.bonjour.src.advertiser":
            advertiser_module_loaded()
            return SimpleNamespace(
                start_gateway_bonjour_advertiser=start_gateway_bonjour_advertiser
            )
        if name == "openclaw.plugin_sdk.runtime":
            runtime_module_loaded()
            return SimpleNamespace(
                register_uncaught_exception_handler=register_uncaught_exception_handler,
                register_unhandled_rejection_handler=register_unhandled_rejection_handler,
            )
        return original_import_module(name, package)

    with patch("importlib.import_module", side_effect=fake_import_module):
        from openclaw_extensions.bonjour import index as bonjour_index

        importlib.reload(bonjour_index)

        assert advertiser_module_loaded.call_count == 0
        assert runtime_module_loaded.call_count == 0

        bonjour_index.default.register(FakeApi())

        assert discovery_service is not None
        assert discovery_service["id"] == "bonjour"
        assert advertiser_module_loaded.call_count == 0
        assert runtime_module_loaded.call_count == 0

        result = await discovery_service["advertise"](
            {
                "machine_display_name": "Dev Box",
                "gateway_port": 3210,
                "gateway_tls_enabled": True,
                "gateway_tls_fingerprint_sha256": "abc123",
                "gateway_direct_reachable": True,
                "canvas_port": 9876,
                "ssh_port": 22,
                "tailnet_dns": "dev.tailnet.ts.net",
                "cli_path": "/usr/local/bin/openclaw",
                "minimal": False,
            }
        )

    assert result == {"stop": stop}
    assert advertiser_module_loaded.call_count == 1
    assert runtime_module_loaded.call_count == 1
    start_gateway_bonjour_advertiser.assert_awaited_once_with(
        {
            "instance_name": "Dev Box (OpenClaw)",
            "gateway_port": 3210,
            "gateway_tls_enabled": True,
            "gateway_tls_fingerprint_sha256": "abc123",
            "gateway_direct_reachable": True,
            "canvas_port": 9876,
            "ssh_port": 22,
            "tailnet_dns": "dev.tailnet.ts.net",
            "cli_path": "/usr/local/bin/openclaw",
            "minimal": False,
        },
        {
            "logger": logger,
            "register_uncaught_exception_handler": register_uncaught_exception_handler,
            "register_unhandled_rejection_handler": register_unhandled_rejection_handler,
        },
    )


def test_bonjour_plugin_entry_metadata() -> None:
    from openclaw_extensions.bonjour import index as bonjour_index

    entry = bonjour_index.default
    assert entry.id == "bonjour"
    assert entry.name == "Bonjour Gateway Discovery"
    assert "Bonjour/mDNS" in entry.description
    assert callable(entry.register)
    assert entry.config_schema is not None
    assert callable(entry.config_schema["safeParse"])


def test_bonjour_plugin_manifest_matches_entry() -> None:
    manifest = json.loads((EXTENSION_ROOT / "openclaw.plugin.json").read_text(encoding="utf-8"))
    from openclaw_extensions.bonjour import index as bonjour_index

    entry = bonjour_index.default
    assert manifest["id"] == entry.id
    assert manifest["name"] == entry.name
    assert manifest["description"] == entry.description
    assert manifest["activation"] == {"onStartup": True}
    assert manifest["enabledByDefaultOnPlatforms"] == ["darwin"]


def test_keeps_ciao_available_in_packaged_startup_runtimes() -> None:
    plugin_package_json_path = TS_EXTENSION_ROOT / "package.json"
    if not plugin_package_json_path.is_file() or not TS_ROOT_PACKAGE_JSON.is_file():
        pytest.skip("TypeScript bonjour package manifests unavailable")

    plugin_package_json = json.loads(plugin_package_json_path.read_text(encoding="utf-8"))
    root_package_json = json.loads(TS_ROOT_PACKAGE_JSON.read_text(encoding="utf-8"))

    assert plugin_package_json.get("dependencies", {}).get("@homebridge/ciao") == "1.3.9"
    assert root_package_json.get("dependencies", {}).get("@homebridge/ciao") == "1.3.9"
    assert plugin_package_json.get("devDependencies", {}).get("@homebridge/ciao") is None
