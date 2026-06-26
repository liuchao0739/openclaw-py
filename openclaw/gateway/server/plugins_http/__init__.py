"""Plugin HTTP route matching and auth helpers.

Mirrors src/gateway/server/plugins-http/. Self-contained port without the
security-path dependency — basic canonicalization is inlined.
"""

from .path_context import (
    PluginRoutePathContext,
    prefix_match_path,
    is_protected_plugin_route_path_from_context,
    resolve_plugin_route_path_context,
)
from .route_match import (
    does_plugin_route_match_path,
    find_matching_plugin_http_routes,
    find_registered_plugin_http_route,
    is_registered_plugin_http_route_path,
)
from .route_auth import (
    matched_plugin_routes_require_gateway_auth,
    should_enforce_gateway_auth_for_plugin_path,
)

__all__ = [
    "PluginRoutePathContext",
    "prefix_match_path",
    "is_protected_plugin_route_path_from_context",
    "resolve_plugin_route_path_context",
    "does_plugin_route_match_path",
    "find_matching_plugin_http_routes",
    "find_registered_plugin_http_route",
    "is_registered_plugin_http_route_path",
    "matched_plugin_routes_require_gateway_auth",
    "should_enforce_gateway_auth_for_plugin_path",
]
