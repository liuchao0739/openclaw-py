"""Tests for the admin-http-rpc extension entry."""

from __future__ import annotations

import json
from pathlib import Path

from openclaw_extensions.admin_http_rpc import index
from openclaw_extensions.admin_http_rpc.src.handler import handle_admin_http_rpc_request

EXTENSION_ROOT = Path(__file__).resolve().parents[2] / "openclaw_extensions" / "admin_http_rpc"
MANIFEST_PATH = EXTENSION_ROOT / "openclaw.plugin.json"


def test_stays_startup_off_until_plugin_entry_explicitly_enabled() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["activation"] == {
        "onStartup": False,
        "onConfigPaths": ["plugins.entries.admin-http-rpc"],
    }
    assert manifest["contracts"] == {
        "gatewayMethodDispatch": ["authenticated-request"],
    }


def test_registers_one_trusted_gateway_http_route() -> None:
    routes: list[dict[str, object]] = []

    class FakeApi:
        def register_http_route(self, route: dict[str, object]) -> None:
            routes.append(route)

    index.default.register(FakeApi())
    assert len(routes) == 1
    assert routes[0]["path"] == "/api/v1/admin/rpc"
    assert routes[0]["auth"] == "gateway"
    assert routes[0]["match"] == "exact"
    assert routes[0]["gateway_runtime_scope_surface"] == "trusted-operator"
    assert routes[0]["handler"] is handle_admin_http_rpc_request
