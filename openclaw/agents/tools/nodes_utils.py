"""Nodes utility helpers.

Provides node list formatting, node identity resolution, and media node helpers
used by nodes-tool implementations.
"""

from __future__ import annotations

from typing import Any


def format_node_display_name(node: dict[str, Any]) -> str:
    """Format a display name for a node."""
    name = node.get("name", "")
    platform = node.get("platform", "")
    if name and platform:
        return f"{name} ({platform})"
    return name or platform or "Unknown"


def is_valid_node_id(node_id: str | None) -> bool:
    """Check if a node id is valid."""
    if not node_id or not isinstance(node_id, str):
        return False
    return len(node_id.strip()) > 0


def resolve_node_by_id(nodes: list[dict[str, Any]], node_id: str) -> dict[str, Any] | None:
    """Find a node by its id in a list."""
    for node in nodes:
        if node.get("id") == node_id:
            return node
    return None


def filter_nodes_by_platform(
    nodes: list[dict[str, Any]],
    platform: str | None,
) -> list[dict[str, Any]]:
    """Filter nodes by platform."""
    if not platform:
        return nodes
    return [n for n in nodes if n.get("platform", "").lower() == platform.lower()]
