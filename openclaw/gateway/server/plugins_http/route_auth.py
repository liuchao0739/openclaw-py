"""Plugin HTTP route auth helpers decide when gateway auth must protect a plugin route path.

Mirrors src/gateway/server/plugins-http/route-auth.ts.
"""

from __future__ import annotations

from typing import Any, Mapping, Union

from .path_context import (
    PluginRoutePathContext,
    is_protected_plugin_route_path_from_context,
    resolve_plugin_route_path_context,
)
from .route_match import find_matching_plugin_http_routes


def matched_plugin_routes_require_gateway_auth(
    routes: list[Mapping[str, Any]],
) -> bool:
    """Gateway-auth decisions for plugin HTTP routes."""
    return any(route.get("auth") == "gateway" for route in routes)


def should_enforce_gateway_auth_for_plugin_path(
    registry: Mapping[str, Any],
    pathname_or_context: Union[str, PluginRoutePathContext],
) -> bool:
    """Return True when a plugin path must pass gateway auth before routing."""
    path_context = (
        resolve_plugin_route_path_context(pathname_or_context)
        if isinstance(pathname_or_context, str)
        else pathname_or_context
    )
    if path_context.malformed_encoding or path_context.decode_pass_limit_reached:
        return True
    if is_protected_plugin_route_path_from_context(path_context):
        return True
    return matched_plugin_routes_require_gateway_auth(
        find_matching_plugin_http_routes(registry, path_context)
    )
