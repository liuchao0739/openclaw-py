"""Admin HTTP RPC plugin entry."""

from openclaw.plugin_sdk.plugin_entry import define_plugin_entry
from openclaw_extensions.admin_http_rpc.src.handler import handle_admin_http_rpc_request


def _register(api):
    api.register_http_route({
        "path": "/api/v1/admin/rpc",
        "auth": "gateway",
        "match": "exact",
        "gatewayRuntimeScopeSurface": "trusted-operator",
        "handler": handle_admin_http_rpc_request,
    })


default = define_plugin_entry(
    id="admin-http-rpc",
    name="Admin HTTP RPC",
    description="Expose selected Gateway admin RPC methods over HTTP",
    register=_register,
)