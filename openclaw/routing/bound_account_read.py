"""Bound account read helpers extract account bindings from channel records.

Mirrors src/routing/bound-account-read.ts.
"""

from __future__ import annotations

from typing import Any

from openclaw.channels.chat_type import normalize_chat_type
from openclaw.routing.binding_scope import (
    normalize_route_binding_channel_id,
    normalize_route_binding_id,
    normalize_route_binding_roles,
    resolve_normalized_route_binding_match,
    route_binding_scope_matches,
)
from openclaw.routing.bindings import list_bindings
from openclaw.routing.peer_kind_match import peer_kind_matches
from openclaw.routing.session_key import normalize_agent_id


def _resolve_normalized_bound_account_match(binding: dict[str, Any]) -> dict[str, Any] | None:
    base_match = resolve_normalized_route_binding_match(binding)
    match = binding.get("match")
    if not base_match or not match or not isinstance(match, dict):
        return None
    peer = match.get("peer") if isinstance(match.get("peer"), dict) else None
    peer_id = (
        peer.get("id").strip() if peer and isinstance(peer.get("id"), str) else None
    )
    peer_kind = normalize_chat_type(peer.get("kind")) if peer else None
    return {
        **base_match,
        "peerId": peer_id or None,
        "peerKind": peer_kind,
        "guildId": normalize_route_binding_id(match.get("guildId")) or None,
        "teamId": normalize_route_binding_id(match.get("teamId")) or None,
        "roles": normalize_route_binding_roles(match.get("roles")),
    }


def _build_exact_peer_id_set(params: dict[str, Any]) -> set[str]:
    exact_peer_ids: set[str] = set()
    peer_id = (params.get("peerId") or "").strip() if params.get("peerId") else ""
    if peer_id:
        exact_peer_ids.add(peer_id)
    for alias in params.get("exactPeerIdAliases") or []:
        trimmed = alias.strip() if isinstance(alias, str) else ""
        if trimmed:
            exact_peer_ids.add(trimmed)
    return exact_peer_ids


def resolve_first_bound_account_id(params: dict[str, Any]) -> str | None:
    cfg = params.get("cfg")
    normalized_channel = normalize_route_binding_channel_id(params.get("channelId"))
    if not normalized_channel:
        return None
    normalized_agent_id = normalize_agent_id(params.get("agentId"))
    normalized_peer_id = (
        params.get("peerId").strip() if isinstance(params.get("peerId"), str) else None
    )
    exact_peer_ids = _build_exact_peer_id_set(
        {
            "peerId": normalized_peer_id,
            "exactPeerIdAliases": params.get("exactPeerIdAliases"),
        }
    )
    has_peer_context = len(exact_peer_ids) > 0
    normalized_peer_kind = normalize_chat_type(params.get("peerKind"))
    wildcard_peer_match: str | None = None
    channel_only_fallback: str | None = None
    for binding in list_bindings(cfg):
        resolved = _resolve_normalized_bound_account_match(binding)
        if (
            not resolved
            or resolved["channelId"] != normalized_channel
            or resolved["agentId"] != normalized_agent_id
        ):
            continue
        if not route_binding_scope_matches(
            resolved,
            {
                "groupSpace": params.get("groupSpace"),
                "memberRoleIds": params.get("memberRoleIds"),
            },
        ):
            continue
        if not has_peer_context:
            return resolved["accountId"]
        if resolved.get("peerId") == "*":
            if (
                not resolved.get("peerKind")
                or not normalized_peer_kind
                or not peer_kind_matches(resolved["peerKind"], normalized_peer_kind)
            ):
                continue
            if wildcard_peer_match is None:
                wildcard_peer_match = resolved["accountId"]
        elif resolved.get("peerId"):
            if (
                resolved.get("peerKind")
                and normalized_peer_kind
                and not peer_kind_matches(resolved["peerKind"], normalized_peer_kind)
            ):
                continue
            if resolved["peerId"] in exact_peer_ids:
                return resolved["accountId"]
        else:
            if channel_only_fallback is None:
                channel_only_fallback = resolved["accountId"]
    return wildcard_peer_match if wildcard_peer_match is not None else channel_only_fallback


__all__ = [
    "resolve_first_bound_account_id",
]
