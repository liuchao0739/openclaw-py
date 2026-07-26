"""Gateway method runtime helpers dispatch plugin calls through the in-process gateway.

Mirrors src/plugin-sdk/gateway-method-runtime.ts.
"""

from __future__ import annotations

from typing import Any, TypedDict

from openclaw.plugins.runtime.gateway_request_scope import get_plugin_runtime_gateway_request_scope


class GatewayMethodDispatchError(TypedDict, total=False):
    code: str
    message: str
    details: Any
    retryable: bool
    retry_after_ms: int


class GatewayMethodDispatchResponse(TypedDict, total=False):
    ok: bool
    payload: Any
    error: GatewayMethodDispatchError
    meta: dict[str, Any]


class GatewayMethodDispatchOptions(TypedDict, total=False):
    expect_final: bool
    timeout_ms: int


async def dispatch_gateway_method(
    method: str,
    params: Any | None = None,
    options: GatewayMethodDispatchOptions | None = None,
) -> GatewayMethodDispatchResponse:
    """Dispatch a Gateway control-plane method from an authenticated plugin request scope."""
    scope = get_plugin_runtime_gateway_request_scope()
    if scope is None or scope.get("gateway_method_dispatch_allowed") is not True:
        plugin_label = (
            f' for plugin "{scope["plugin_id"]}"'
            if scope is not None and scope.get("plugin_id")
            else ""
        )
        raise RuntimeError(
            "Gateway method dispatch is reserved for plugin HTTP routes that declare "
            f'contracts.gatewayMethodDispatch: ["authenticated-request"]{plugin_label}.'
        )

    from openclaw.gateway.server_plugins import (
        dispatch_gateway_method_in_process_raw,
    )

    dispatch_options: dict[str, Any] = {
        "disableSyntheticClient": True,
        "requireScopedClient": True,
    }
    if options is not None:
        if options.get("expect_final") is not None:
            dispatch_options["expectFinal"] = options["expect_final"]
        if options.get("timeout_ms") is not None:
            dispatch_options["timeoutMs"] = options["timeout_ms"]

    return await dispatch_gateway_method_in_process_raw(method, params, dispatch_options)
