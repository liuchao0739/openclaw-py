"""Manifest capability availability helpers.

Checks whether a tool manifest declares support for specific capabilities.
"""

from __future__ import annotations

from typing import Any


def has_capability(manifest: dict[str, Any] | None, capability: str) -> bool:
    """Check if a manifest declares a specific capability."""
    if not manifest:
        return False
    capabilities = manifest.get("capabilities")
    if isinstance(capabilities, list):
        return capability in capabilities
    if isinstance(capabilities, dict):
        return capabilities.get(capability, False) is not False
    return False


def get_available_capabilities(manifest: dict[str, Any] | None) -> list[str]:
    """Get the list of available capabilities from a manifest."""
    if not manifest:
        return []
    capabilities = manifest.get("capabilities")
    if isinstance(capabilities, list):
        return [str(c) for c in capabilities]
    if isinstance(capabilities, dict):
        return [k for k, v in capabilities.items() if v is not False]
    return []


def is_tool_available(manifest: dict[str, Any] | None, tool_name: str) -> bool:
    """Check if a specific tool is available in the manifest."""
    if not manifest:
        return False
    tools = manifest.get("tools")
    if isinstance(tools, list):
        return any(
            (t.get("name") == tool_name if isinstance(t, dict) else t == tool_name)
            for t in tools
        )
    if isinstance(tools, dict):
        return tool_name in tools
    return False


def filter_available_tools(
    manifest: dict[str, Any] | None,
    requested_tools: list[str],
) -> list[str]:
    """Filter a list of requested tools to only those available in the manifest."""
    if not manifest:
        return []
    return [t for t in requested_tools if is_tool_available(manifest, t)]
