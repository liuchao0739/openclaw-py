"""Tests for gateway/server/plugins-http modules."""

import pytest

from openclaw.gateway.server.plugins_http.path_context import (
    prefix_match_path,
    is_protected_plugin_route_path_from_context,
    resolve_plugin_route_path_context,
    PluginRoutePathContext,
)
from openclaw.gateway.server.plugins_http.route_match import (
    does_plugin_route_match_path,
    find_matching_plugin_http_routes,
    find_registered_plugin_http_route,
    is_registered_plugin_http_route_path,
)
from openclaw.gateway.server.plugins_http.route_auth import (
    matched_plugin_routes_require_gateway_auth,
    should_enforce_gateway_auth_for_plugin_path,
)


class TestPrefixMatchPath:
    def test_exact_match(self):
        assert prefix_match_path("/admin", "/admin") is True

    def test_subpath_match(self):
        assert prefix_match_path("/admin/users", "/admin") is True

    def test_no_match(self):
        assert prefix_match_path("/public", "/admin") is False

    def test_percent_encoded_boundary(self):
        assert prefix_match_path("/admin%2f", "/admin") is True

    def test_partial_no_match(self):
        assert prefix_match_path("/administrator", "/admin") is False


class TestPathContext:
    def test_simple_path(self):
        ctx = resolve_plugin_route_path_context("/api/v1")
        assert ctx.pathname == "/api/v1"
        assert len(ctx.candidates) >= 1

    def test_encoded_path(self):
        ctx = resolve_plugin_route_path_context("/api/%2e%2e/secret")
        assert len(ctx.candidates) >= 2

    def test_protected_admin(self):
        ctx = resolve_plugin_route_path_context("/admin/settings")
        assert is_protected_plugin_route_path_from_context(ctx) is True

    def test_protected_internal(self):
        ctx = resolve_plugin_route_path_context("/internal/debug")
        assert is_protected_plugin_route_path_from_context(ctx) is True

    def test_not_protected(self):
        ctx = resolve_plugin_route_path_context("/public/info")
        assert is_protected_plugin_route_path_from_context(ctx) is False


class TestRouteMatch:
    def test_exact_match(self):
        registry = {"http_routes": [{"path": "/api/hook", "match": "exact"}]}
        ctx = resolve_plugin_route_path_context("/api/hook")
        matches = find_matching_plugin_http_routes(registry, ctx)
        assert len(matches) == 1

    def test_prefix_match(self):
        registry = {"http_routes": [{"path": "/api", "match": "prefix"}]}
        ctx = resolve_plugin_route_path_context("/api/sub/path")
        matches = find_matching_plugin_http_routes(registry, ctx)
        assert len(matches) == 1

    def test_no_match(self):
        registry = {"http_routes": [{"path": "/api", "match": "exact"}]}
        ctx = resolve_plugin_route_path_context("/other")
        matches = find_matching_plugin_http_routes(registry, ctx)
        assert len(matches) == 0

    def test_exact_before_prefix(self):
        registry = {
            "http_routes": [
                {"path": "/api", "match": "prefix"},
                {"path": "/api/special", "match": "exact"},
            ]
        }
        ctx = resolve_plugin_route_path_context("/api/special")
        matches = find_matching_plugin_http_routes(registry, ctx)
        assert matches[0]["path"] == "/api/special"

    def test_find_registered_route(self):
        registry = {"http_routes": [{"path": "/hook", "match": "exact"}]}
        assert find_registered_plugin_http_route(registry, "/hook") is not None
        assert find_registered_plugin_http_route(registry, "/nope") is None

    def test_is_registered(self):
        registry = {"http_routes": [{"path": "/hook", "match": "exact"}]}
        assert is_registered_plugin_http_route_path(registry, "/hook") is True
        assert is_registered_plugin_http_route_path(registry, "/nope") is False

    def test_empty_routes(self):
        registry = {"http_routes": []}
        ctx = resolve_plugin_route_path_context("/anything")
        assert find_matching_plugin_http_routes(registry, ctx) == []

    def test_no_routes_key(self):
        registry = {}
        ctx = resolve_plugin_route_path_context("/anything")
        assert find_matching_plugin_http_routes(registry, ctx) == []

    def test_httpRoutes_camelCase(self):
        registry = {"httpRoutes": [{"path": "/hook", "match": "exact"}]}
        assert find_registered_plugin_http_route(registry, "/hook") is not None


class TestRouteAuth:
    def test_gateway_auth_required(self):
        routes = [{"auth": "gateway"}, {"auth": "none"}]
        assert matched_plugin_routes_require_gateway_auth(routes) is True

    def test_no_gateway_auth(self):
        routes = [{"auth": "none"}, {"auth": "optional"}]
        assert matched_plugin_routes_require_gateway_auth(routes) is False

    def test_protected_path_enforces_auth(self):
        registry = {"http_routes": []}
        assert should_enforce_gateway_auth_for_plugin_path(registry, "/admin/x") is True

    def test_non_protected_no_auth(self):
        registry = {"http_routes": [{"path": "/public", "match": "exact", "auth": "none"}]}
        assert should_enforce_gateway_auth_for_plugin_path(registry, "/public") is False

    def test_gateway_auth_route_enforces(self):
        registry = {"http_routes": [{"path": "/hook", "match": "exact", "auth": "gateway"}]}
        assert should_enforce_gateway_auth_for_plugin_path(registry, "/hook") is True

    def test_context_object_accepted(self):
        registry = {"http_routes": []}
        ctx = resolve_plugin_route_path_context("/public")
        assert should_enforce_gateway_auth_for_plugin_path(registry, ctx) is False
