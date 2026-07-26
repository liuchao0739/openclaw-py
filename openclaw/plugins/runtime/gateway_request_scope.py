"""Gateway request scope tracks request-local plugin runtime context across async work.

Mirrors src/plugins/runtime/gateway-request-scope.ts.
"""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from typing import Any, TypedDict, TypeVar

T = TypeVar("T")


class PluginRuntimeGatewayRequestScope(TypedDict, total=False):
    context: Any
    client: Any
    is_webchat_connect: Any
    plugin_id: str
    plugin_source: str
    gateway_method_dispatch_allowed: bool


class PluginRuntimePluginScope(TypedDict):
    plugin_id: str
    plugin_source: str | None


_plugin_runtime_gateway_request_scope: ContextVar[PluginRuntimeGatewayRequestScope | None] = (
    ContextVar("openclaw.plugin_runtime_gateway_request_scope", default=None)
)


def with_plugin_runtime_gateway_request_scope(
    scope: PluginRuntimeGatewayRequestScope,
    run: Callable[[], T],
) -> T:
    """Run plugin gateway handlers with request-scoped context runtime helpers can read."""
    token = _plugin_runtime_gateway_request_scope.set(scope)
    try:
        return run()
    finally:
        _plugin_runtime_gateway_request_scope.reset(token)


def with_plugin_runtime_plugin_scope(
    scope: PluginRuntimePluginScope,
    run: Callable[[], T],
) -> T:
    """Run work under the current gateway request scope while attaching plugin identity."""
    current = _plugin_runtime_gateway_request_scope.get()
    scoped: PluginRuntimeGatewayRequestScope
    if current is not None:
        scoped = {**current, "plugin_id": scope["plugin_id"]}
    else:
        scoped = {
            "plugin_id": scope["plugin_id"],
            "is_webchat_connect": lambda: False,
        }
    if scope.get("plugin_source") is not None:
        scoped["plugin_source"] = scope["plugin_source"]
    else:
        scoped.pop("plugin_source", None)
    return with_plugin_runtime_gateway_request_scope(scoped, run)


def with_plugin_runtime_plugin_id_scope(plugin_id: str, run: Callable[[], T]) -> T:
    """Run work under the current gateway request scope while attaching plugin identity."""
    return with_plugin_runtime_plugin_scope({"plugin_id": plugin_id, "plugin_source": None}, run)


def get_plugin_runtime_gateway_request_scope() -> PluginRuntimeGatewayRequestScope | None:
    """Return the current plugin gateway request scope from a plugin request handler."""
    return _plugin_runtime_gateway_request_scope.get()
