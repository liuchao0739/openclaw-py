"""Gateway server test utilities build plugin-registry fixtures for nested server suites.

Mirrors src/gateway/server/__tests__/test-utils.ts.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def create_empty_plugin_registry() -> dict[str, Any]:
    """Return an empty plugin registry fixture."""
    return {
        "gateway_handlers": {},
        "http_routes": [],
    }


def create_test_registry(overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Create a shared plugin-registry fixture for gateway server tests.

    Merges overrides onto an empty registry, ensuring ``gateway_handlers`` and
    ``http_routes`` are always present.
    """
    merged = create_empty_plugin_registry()
    if overrides:
        for k, v in overrides.items():
            merged[k] = deepcopy(v)
    merged.setdefault("gateway_handlers", {})
    merged.setdefault("http_routes", [])
    return merged
