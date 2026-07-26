"""Admin HTTP RPC plugin entry.

It exposes a trusted gateway-authenticated HTTP endpoint for the explicit admin
method allowlist.
"""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.admin_http_rpc.src.handler import handle_admin_http_rpc_request


def _register(api: OpenClawPluginApi) -> None:
    api.register_http_route(
        {
            "path": "/api/v1/admin/rpc",
            "auth": "gateway",
            "match": "exact",
            "gateway_runtime_scope_surface": "trusted-operator",
            "handler": handle_admin_http_rpc_request,
        }
    )


default = define_plugin_entry(
    id="admin-http-rpc",
    name="Admin HTTP RPC",
    description="Expose selected Gateway admin RPC methods over HTTP",
    register=_register,
)
