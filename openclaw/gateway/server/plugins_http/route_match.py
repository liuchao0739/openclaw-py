"""Plugin HTTP route matching against canonicalized request paths.

Mirrors src/gateway/server/plugins-http/route-match.ts.
"""

from __future__ import annotations

from typing import Any, Mapping

from .path_context import (
    PluginRoutePathContext,
    prefix_match_path,
    resolve_plugin_route_path_context,
)


def _canonicalize_path_variant(path: str) -> str:
    """Canonicalize a route path variant for matching."""
    if not isinstance(path, str):
        return ""
    return path.strip().lower()


def does_plugin_route_match_path(
    route: Mapping[str, Any],
    context: PluginRoutePathContext,
) -> bool:
    """Return True when a registered route matches any canonical request candidate."""
    route_canonical = _canonicalize_path_variant(route.get("path", ""))
    if route.get("match") == "prefix":
        return any(
            prefix_match_path(candidate, route_canonical)
            for candidate in context.candidates
        )
    return any(candidate == route_canonical for candidate in context.candidates)


def find_matching_plugin_http_routes(
    registry: Mapping[str, Any],
    context: PluginRoutePathContext,
) -> list[dict[str, Any]]:
    """Find matching plugin routes with exact matches ordered before prefix matches."""
    routes = registry.get("http_routes") or registry.get("httpRoutes") or []
    if not routes:
        return []
    exact_matches: list[dict[str, Any]] = []
    prefix_matches: list[dict[str, Any]] = []
    for route in routes:
        if not does_plugin_route_match_path(route, context):
            continue
        if route.get("match") == "prefix":
            prefix_matches.append(route)
        else:
            exact_matches.append(route)
    exact_matches.sort(key=lambda r: len(r.get("path", "")), reverse=True)
    prefix_matches.sort(key=lambda r: len(r.get("path", "")), reverse=True)
    return [*exact_matches, *prefix_matches]


def find_registered_plugin_http_route(
    registry: Mapping[str, Any],
    pathname: str,
) -> dict[str, Any] | None:
    """Return the first registered plugin HTTP route for a raw request path."""
    context = resolve_plugin_route_path_context(pathname)
    matches = find_matching_plugin_http_routes(registry, context)
    return matches[0] if matches else None


def is_registered_plugin_http_route_path(
    registry: Mapping[str, Any],
    pathname: str,
) -> bool:
    """Convenience predicate for checking whether a raw path is a plugin HTTP route."""
    return find_registered_plugin_http_route(registry, pathname) is not None
