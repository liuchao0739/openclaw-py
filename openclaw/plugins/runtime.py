from __future__ import annotations

from typing import Any


def resolve_plugin_runtime(api_id: str) -> str:
    parts = api_id.split(":", 1)
    if len(parts) == 2:
        return parts[0]
    return "generic"


def resolve_plugin_capability(api_id: str) -> str:
    parts = api_id.split(":", 1)
    if len(parts) == 2:
        return parts[1]
    return api_id


def build_api_id(runtime: str, capability: str) -> str:
    return f"{runtime}:{capability}"


RESERVED_PLUGIN_RUNTIMES: set[str] = {
    "agent",
    "app",
    "internal",
}
