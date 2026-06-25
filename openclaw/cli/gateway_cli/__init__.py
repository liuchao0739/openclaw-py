"""Gateway CLI — runtime hooks, shared helpers, RPC call."""

from openclaw.cli.gateway_cli.call import (
    DEFAULT_GATEWAY_RPC_TIMEOUT_MS,
    GatewayRpcOpts,
    call_gateway_cli,
    parse_timeout_ms_with_fallback,
)
from openclaw.cli.gateway_cli.runtime_hooks import (
    get_gateway_run_runtime_hooks,
    install_gateway_run_runtime_hooks,
)
from openclaw.cli.gateway_cli.shared import (
    maybe_explain_gateway_service_stop,
    render_gateway_service_stop_hints,
)

__all__ = [
    "DEFAULT_GATEWAY_RPC_TIMEOUT_MS",
    "GatewayRpcOpts",
    "call_gateway_cli",
    "get_gateway_run_runtime_hooks",
    "install_gateway_run_runtime_hooks",
    "maybe_explain_gateway_service_stop",
    "parse_timeout_ms_with_fallback",
    "render_gateway_service_stop_hints",
]
