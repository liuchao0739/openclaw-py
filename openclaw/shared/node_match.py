"""Node match helpers score and select nodes from names, ids, and addresses."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


def _normalize_lowercase_or_empty(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def _normalize_optional_lowercase_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip().lower() or None


def _normalize_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value or None


def normalize_node_key(value: str) -> str:
    normalized = _normalize_lowercase_or_empty(value)
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def _list_known_nodes(nodes: list[dict[str, Any]]) -> str:
    parts = []
    for n in nodes:
        entry = n.get("displayName") or n.get("remoteIp") or n.get("nodeId")
        if entry:
            parts.append(entry)
    return ", ".join(parts)


def _format_node_candidate_label(node: dict[str, Any]) -> str:
    label = node.get("displayName") or node.get("remoteIp") or node.get("nodeId") or ""
    details = [f"node={node.get('nodeId', '')}"]
    client_id = _normalize_optional_string(node.get("clientId"))
    if client_id:
        details.append(f"client={client_id}")
    return f"{label} [{', '.join(details)}]"


def _is_current_openclaw_client(client_id: Any) -> bool:
    normalized = _normalize_optional_lowercase_string(client_id) or ""
    return normalized.startswith("openclaw-")


def _is_legacy_clawdbot_client(client_id: Any) -> bool:
    normalized = _normalize_optional_lowercase_string(client_id) or ""
    return normalized.startswith("clawdbot-") or normalized.startswith("moldbot-")


def _pick_preferred_legacy_migration_match(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    current = [m for m in matches if _is_current_openclaw_client(m.get("clientId"))]
    if len(current) != 1:
        return None
    legacy_count = sum(1 for m in matches if _is_legacy_clawdbot_client(m.get("clientId")))
    if legacy_count == 0 or len(current) + legacy_count != len(matches):
        return None
    return current[0]


def _resolve_match_score(node: dict[str, Any], query: str, query_normalized: str) -> int:
    node_id = node.get("nodeId", "")
    if node_id == query:
        return 4000
    remote_ip = node.get("remoteIp")
    if isinstance(remote_ip, str) and remote_ip == query:
        return 3000
    name = node.get("displayName")
    if isinstance(name, str) and normalize_node_key(name) == query_normalized:
        return 2000
    if len(query) >= 6 and isinstance(node_id, str) and node_id.startswith(query):
        return 1000
    return 0


def _score_node_candidate(node: dict[str, Any], match_score: int) -> int:
    score = match_score
    if node.get("connected") is True:
        score += 100
    if _is_current_openclaw_client(node.get("clientId")):
        score += 10
    elif _is_legacy_clawdbot_client(node.get("clientId")):
        score -= 10
    return score


def resolve_node_id_from_candidates(nodes: list[dict[str, Any]], query: str) -> str:
    q = query.strip()
    if not q:
        raise ValueError("node required")

    trimmed = _normalize_optional_string(q) or ""
    if not trimmed:
        raise ValueError("node required")
    normalized = normalize_node_key(trimmed)

    raw_matches: list[dict[str, Any]] = []
    for node in nodes:
        match_score = _resolve_match_score(node, trimmed, normalized)
        if match_score == 0:
            continue
        raw_matches.append({
            "node": node,
            "matchScore": match_score,
            "selectionScore": _score_node_candidate(node, match_score),
        })

    if len(raw_matches) == 1:
        return raw_matches[0]["node"].get("nodeId", "")
    if len(raw_matches) == 0:
        known = _list_known_nodes(nodes)
        raise ValueError(f"unknown node: {q}{f' (known: {known})' if known else ''}")

    top_match_score = max(m["matchScore"] for m in raw_matches)
    strongest = [m for m in raw_matches if m["matchScore"] == top_match_score]
    if len(strongest) == 1:
        return strongest[0]["node"].get("nodeId", "")

    top_selection = max(m["selectionScore"] for m in strongest)
    matches = [m for m in strongest if m["selectionScore"] == top_selection]
    if len(matches) == 1:
        return matches[0]["node"].get("nodeId", "")

    preferred = _pick_preferred_legacy_migration_match([m["node"] for m in matches])
    if preferred:
        return preferred.get("nodeId", "")

    raise ValueError(
        f"ambiguous node: {q} (matches: {', '.join(_format_node_candidate_label(m['node']) for m in matches)})"
    )
