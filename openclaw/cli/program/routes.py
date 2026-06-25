"""Routed command lookup for fast paths that bypass full command registration."""

from __future__ import annotations

from typing import Any, Callable


class RouteSpec:
    """Specification for a routed command."""

    def __init__(
        self,
        path: list[str],
        matches: Callable[[list[str]], bool] | None = None,
        can_run: Callable[[list[str]], bool] | None = None,
    ) -> None:
        self.path = path
        self._matches = matches or self._default_matches
        self.can_run = can_run

    def _default_matches(self, command_path: list[str]) -> bool:
        if len(command_path) < len(self.path):
            return False
        return command_path[:len(self.path)] == self.path

    def matches(self, command_path: list[str]) -> bool:
        return self._matches(command_path)


# Registered routes (populated by route-specs module when available)
_routed_commands: list[RouteSpec] = []


def register_route(route: RouteSpec) -> None:
    """Register a routed command."""
    _routed_commands.append(route)


def find_routed_command(path: list[str], argv: list[str] | None = None) -> RouteSpec | None:
    """Find the first route matching a command path and parseable argv."""
    for route in _routed_commands:
        if route.matches(path):
            if argv and route.can_run and not route.can_run(argv):
                continue
            return route
    return None
