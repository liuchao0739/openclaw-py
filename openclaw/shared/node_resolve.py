"""Node resolution helpers resolve node references from names, ids, and URLs."""

from __future__ import annotations

from typing import Any, Callable

from .node_match import resolve_node_id_from_candidates


def _normalize_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value or None


def resolve_node_id_from_node_list(
    nodes: list[dict[str, Any]],
    query: str | None = None,
    allow_default: bool = False,
    pick_default_node: Callable[[list[dict[str, Any]]], dict[str, Any] | None] | None = None,
) -> str:
    q = _normalize_optional_string(query) or ""
    if not q:
        if allow_default and pick_default_node:
            picked = pick_default_node(nodes)
            if picked:
                return picked.get("nodeId", "")
        raise ValueError("node required")
    return resolve_node_id_from_candidates(nodes, q)


def resolve_node_from_node_list(
    nodes: list[dict[str, Any]],
    query: str | None = None,
    allow_default: bool = False,
    pick_default_node: Callable[[list[dict[str, Any]]], dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    node_id = resolve_node_id_from_node_list(nodes, query, allow_default, pick_default_node)
    for node in nodes:
        if node.get("nodeId") == node_id:
            return node
    return {"nodeId": node_id}
