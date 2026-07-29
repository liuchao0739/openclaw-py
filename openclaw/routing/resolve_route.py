"""Route resolution helpers map user targets to configured channel routes.

Mirrors src/routing/resolve-route.ts.
"""

from __future__ import annotations

from typing import Any, Literal

from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty
from openclaw.channels.chat_type import ChatType, normalize_chat_type
from openclaw.routing.binding_scope import (
    normalize_route_binding_id,
    normalize_route_binding_roles,
    route_binding_scope_matches,
)
from openclaw.routing.bindings import list_bindings
from openclaw.routing.peer_kind_match import peer_kind_matches
from openclaw.routing.session_key import (
    DEFAULT_ACCOUNT_ID,
    DEFAULT_MAIN_KEY,
    build_agent_main_session_key,
    build_agent_peer_session_key,
    normalize_account_id,
    normalize_agent_id,
    sanitize_agent_id,
)

RoutePeerKind = ChatType


class RoutePeer(dict):
    kind: ChatType
    id: str


ResolveAgentRouteInput = dict[str, Any]
ResolvedAgentRoute = dict[str, Any]
LastRoutePolicy = Literal["main", "session"]
MatchedBy = Literal[
    "binding.peer",
    "binding.peer.parent",
    "binding.peer.wildcard",
    "binding.guild+roles",
    "binding.guild",
    "binding.team",
    "binding.account",
    "binding.channel",
    "default",
]


def _should_log_verbose() -> bool:
    return False


def _log_debug(message: str) -> None:
    pass


def _normalize_token(value: str | None) -> str:
    return normalize_lowercase_string_or_empty(value)


def _normalize_id(value: Any) -> str:
    return normalize_route_binding_id(value)


def derive_last_route_policy(params: dict[str, Any]) -> LastRoutePolicy:
    return "main" if params["sessionKey"] == params["mainSessionKey"] else "session"


def resolve_inbound_last_route_session_key(params: dict[str, Any]) -> str:
    route = params["route"]
    return (
        route["mainSessionKey"]
        if route["lastRoutePolicy"] == "main"
        else params["sessionKey"]
    )


def build_agent_session_key(params: dict[str, Any]) -> str:
    channel = _normalize_token(params.get("channel")) or "unknown"
    peer = params.get("peer")
    return build_agent_peer_session_key(
        {
            "agentId": params.get("agentId"),
            "mainKey": DEFAULT_MAIN_KEY,
            "channel": channel,
            "accountId": params.get("accountId"),
            "peerKind": (peer or {}).get("kind") if peer else "direct",
            "peerId": _normalize_id(peer.get("id")) or "unknown" if peer else None,
            "dmScope": params.get("dmScope"),
            "identityLinks": params.get("identityLinks"),
        }
    )


def _list_agents(cfg: Any) -> list[Any]:
    agents = getattr(cfg, "agents", None) if cfg else None
    agent_list = agents.get("list") if isinstance(agents, dict) else None
    return agent_list if isinstance(agent_list, list) else []


def _resolve_default_agent_id(cfg: Any) -> str:
    agents = getattr(cfg, "agents", None) if cfg else None
    if agents and isinstance(agents, dict):
        default_id = agents.get("default")
        if isinstance(default_id, str) and default_id.strip():
            return default_id.strip()
    return "main"


_agent_lookup_cache: dict[int, dict[str, Any]] = {}


def _resolve_agent_lookup_cache(cfg: Any) -> dict[str, Any]:
    cfg_id = id(cfg)
    agents_ref = getattr(cfg, "agents", None) if cfg else None
    existing = _agent_lookup_cache.get(cfg_id)
    if existing and existing.get("agentsRef") is agents_ref:
        return existing
    by_normalized_id: dict[str, str] = {}
    for agent in _list_agents(cfg):
        raw_id = agent.get("id") if isinstance(agent, dict) else None
        raw_id = raw_id.strip() if isinstance(raw_id, str) else ""
        if not raw_id:
            continue
        by_normalized_id[normalize_agent_id(raw_id)] = sanitize_agent_id(raw_id)
    next_cache = {
        "agentsRef": agents_ref,
        "byNormalizedId": by_normalized_id,
        "fallbackDefaultAgentId": sanitize_agent_id(_resolve_default_agent_id(cfg)),
    }
    _agent_lookup_cache[cfg_id] = next_cache
    return next_cache


def pick_first_existing_agent_id(cfg: Any, agent_id: str) -> str:
    lookup = _resolve_agent_lookup_cache(cfg)
    trimmed = (agent_id or "").strip()
    if not trimmed:
        return lookup["fallbackDefaultAgentId"]
    normalized = normalize_agent_id(trimmed)
    if len(lookup["byNormalizedId"]) == 0:
        return sanitize_agent_id(trimmed)
    resolved = lookup["byNormalizedId"].get(normalized)
    if resolved:
        return resolved
    return lookup["fallbackDefaultAgentId"]


def _normalize_peer_constraint(
    peer: dict[str, Any] | None,
) -> dict[str, Any]:
    if not peer:
        return {"state": "none"}
    kind = normalize_chat_type(peer.get("kind"))
    id_value = _normalize_id(peer.get("id"))
    if not kind or not id_value:
        return {"state": "invalid"}
    if id_value == "*":
        return {"state": "wildcard-kind", "kind": kind}
    return {"state": "valid", "kind": kind, "id": id_value}


def _normalize_binding_match(match: dict[str, Any] | None) -> dict[str, Any]:
    raw_roles = match.get("roles") if match else None
    return {
        "accountPattern": (match.get("accountId") or "").strip() if match else "",
        "peer": _normalize_peer_constraint(match.get("peer") if match else None),
        "guildId": _normalize_id(match.get("guildId")) if match else "",
        "teamId": _normalize_id(match.get("teamId")) if match else "",
        "roles": normalize_route_binding_roles(raw_roles),
    }


def _resolve_account_pattern_key(account_pattern: str) -> str:
    if not account_pattern.strip():
        return DEFAULT_ACCOUNT_ID
    return normalize_account_id(account_pattern)


_evaluated_bindings_cache: dict[int, dict[str, Any]] = {}
_MAX_EVALUATED_BINDINGS_CACHE_KEYS = 2000
_resolved_route_cache: dict[int, dict[str, Any]] = {}
_MAX_RESOLVED_ROUTE_CACHE_KEYS = 4000


def _build_evaluated_bindings_by_channel(cfg: Any) -> dict[str, dict[str, Any]]:
    by_channel: dict[str, dict[str, Any]] = {}
    order = 0
    for binding in list_bindings(cfg):
        if not binding or not isinstance(binding, dict):
            continue
        match_obj = binding.get("match")
        channel = _normalize_token(match_obj.get("channel") if isinstance(match_obj, dict) else None)
        if not channel:
            continue
        match = _normalize_binding_match(match_obj if isinstance(match_obj, dict) else None)
        evaluated = {"binding": binding, "match": match, "order": order}
        order += 1
        bucket = by_channel.get(channel)
        if not bucket:
            bucket = {"byAccount": {}, "byAnyAccount": []}
            by_channel[channel] = bucket
        if match["accountPattern"] == "*":
            bucket["byAnyAccount"].append(evaluated)
            continue
        account_key = _resolve_account_pattern_key(match["accountPattern"])
        bucket["byAccount"].setdefault(account_key, []).append(evaluated)
    return by_channel


def _merge_evaluated_bindings_in_source_order(
    account_scoped: list[dict[str, Any]], any_account: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if len(account_scoped) == 0:
        return any_account
    if len(any_account) == 0:
        return account_scoped
    merged: list[dict[str, Any]] = []
    account_idx = 0
    any_idx = 0
    while account_idx < len(account_scoped) and any_idx < len(any_account):
        account_binding = account_scoped[account_idx]
        any_binding = any_account[any_idx]
        if (account_binding.get("order", float("inf"))) <= (any_binding.get("order", float("inf"))):
            merged.append(account_binding)
            account_idx += 1
        else:
            merged.append(any_binding)
            any_idx += 1
    if account_idx < len(account_scoped):
        merged.extend(account_scoped[account_idx:])
    if any_idx < len(any_account):
        merged.extend(any_account[any_idx:])
    return merged


def _push_to_index_map(
    index_map: dict[str, list[dict[str, Any]]], key: str | None, binding: dict[str, Any]
) -> None:
    if not key:
        return
    index_map.setdefault(key, []).append(binding)


def _peer_lookup_keys(kind: str, id_value: str) -> list[str]:
    if kind == "group":
        return [f"group:{id_value}", f"channel:{id_value}"]
    if kind == "channel":
        return [f"channel:{id_value}", f"group:{id_value}"]
    return [f"{kind}:{id_value}"]


def _build_evaluated_bindings_index(
    bindings: list[dict[str, Any]],
) -> dict[str, Any]:
    by_peer: dict[str, list[dict[str, Any]]] = {}
    by_peer_wildcard: list[dict[str, Any]] = []
    by_guild_with_roles: dict[str, list[dict[str, Any]]] = {}
    by_guild: dict[str, list[dict[str, Any]]] = {}
    by_team: dict[str, list[dict[str, Any]]] = {}
    by_account: list[dict[str, Any]] = []
    by_channel: list[dict[str, Any]] = []
    for binding in bindings:
        peer_state = binding["match"]["peer"]["state"]
        if peer_state == "valid":
            for key in _peer_lookup_keys(
                binding["match"]["peer"]["kind"], binding["match"]["peer"]["id"]
            ):
                _push_to_index_map(by_peer, key, binding)
            continue
        if peer_state == "wildcard-kind":
            by_peer_wildcard.append(binding)
            continue
        if binding["match"]["guildId"] and binding["match"]["roles"]:
            _push_to_index_map(by_guild_with_roles, binding["match"]["guildId"], binding)
            continue
        if binding["match"]["guildId"] and not binding["match"]["roles"]:
            _push_to_index_map(by_guild, binding["match"]["guildId"], binding)
            continue
        if binding["match"]["teamId"]:
            _push_to_index_map(by_team, binding["match"]["teamId"], binding)
            continue
        if binding["match"]["accountPattern"] != "*":
            by_account.append(binding)
            continue
        by_channel.append(binding)
    return {
        "byPeer": by_peer,
        "byPeerWildcard": by_peer_wildcard,
        "byGuildWithRoles": by_guild_with_roles,
        "byGuild": by_guild,
        "byTeam": by_team,
        "byAccount": by_account,
        "byChannel": by_channel,
    }


def _get_evaluated_bindings_for_channel_account(
    cfg: Any, channel: str, account_id: str
) -> list[dict[str, Any]]:
    bindings_ref = getattr(cfg, "bindings", None) if cfg else None
    cfg_id = id(cfg)
    existing = _evaluated_bindings_cache.get(cfg_id)
    if existing and existing.get("bindingsRef") is bindings_ref:
        cache = existing
    else:
        cache = {
            "bindingsRef": bindings_ref,
            "byChannel": _build_evaluated_bindings_by_channel(cfg),
            "byChannelAccount": {},
            "byChannelAccountIndex": {},
        }
        _evaluated_bindings_cache[cfg_id] = cache
    cache_key = f"{channel}\t{account_id}"
    hit = cache["byChannelAccount"].get(cache_key)
    if hit:
        return hit
    channel_bindings = cache["byChannel"].get(channel)
    account_scoped = channel_bindings["byAccount"].get(account_id, []) if channel_bindings else []
    any_account = channel_bindings["byAnyAccount"] if channel_bindings else []
    evaluated = _merge_evaluated_bindings_in_source_order(account_scoped, any_account)
    cache["byChannelAccount"][cache_key] = evaluated
    cache["byChannelAccountIndex"][cache_key] = _build_evaluated_bindings_index(evaluated)
    if len(cache["byChannelAccount"]) > _MAX_EVALUATED_BINDINGS_CACHE_KEYS:
        cache["byChannelAccount"].clear()
        cache["byChannelAccountIndex"].clear()
        cache["byChannelAccount"][cache_key] = evaluated
        cache["byChannelAccountIndex"][cache_key] = _build_evaluated_bindings_index(evaluated)
    return evaluated


def _get_evaluated_binding_index_for_channel_account(
    cfg: Any, channel: str, account_id: str
) -> dict[str, Any]:
    _get_evaluated_bindings_for_channel_account(cfg, channel, account_id)
    existing = _evaluated_bindings_cache.get(id(cfg))
    cache_key = f"{channel}\t{account_id}"
    indexed = existing["byChannelAccountIndex"].get(cache_key) if existing else None
    if indexed:
        return indexed
    built = _build_evaluated_bindings_index(
        _get_evaluated_bindings_for_channel_account(cfg, channel, account_id)
    )
    if existing:
        existing["byChannelAccountIndex"][cache_key] = built
    return built


def _resolve_route_cache_for_config(cfg: Any) -> dict[str, ResolvedAgentRoute]:
    cfg_id = id(cfg)
    bindings_ref = getattr(cfg, "bindings", None) if cfg else None
    agents_ref = getattr(cfg, "agents", None) if cfg else None
    session_ref = getattr(cfg, "session", None) if cfg else None
    existing = _resolved_route_cache.get(cfg_id)
    if (
        existing
        and existing.get("bindingsRef") is bindings_ref
        and existing.get("agentsRef") is agents_ref
        and existing.get("sessionRef") is session_ref
    ):
        return existing["byKey"]
    by_key: dict[str, ResolvedAgentRoute] = {}
    _resolved_route_cache[cfg_id] = {
        "bindingsRef": bindings_ref,
        "agentsRef": agents_ref,
        "sessionRef": session_ref,
        "byKey": by_key,
    }
    return by_key


def _format_route_cache_peer(peer: dict[str, Any] | None) -> str:
    if not peer or not peer.get("id"):
        return "-"
    return f"{peer['kind']}:{peer['id']}"


def _format_role_ids_cache_key(role_ids: list[str]) -> str:
    count = len(role_ids)
    if count == 0:
        return "-"
    if count == 1:
        return role_ids[0] or "-"
    if count == 2:
        first = role_ids[0] or ""
        second = role_ids[1] or ""
        return f"{first},{second}" if first <= second else f"{second},{first}"
    return ",".join(sorted(role_ids))


def _build_resolved_route_cache_key(params: dict[str, Any]) -> str:
    return "\t".join(
        [
            params["channel"],
            params["accountId"],
            _format_route_cache_peer(params["peer"]),
            _format_route_cache_peer(params["parentPeer"]),
            params["guildId"] or "-",
            params["teamId"] or "-",
            _format_role_ids_cache_key(params["memberRoleIds"]),
            params["dmScope"],
        ]
    )


def _has_guild_constraint(match: dict[str, Any]) -> bool:
    return bool(match["guildId"])


def _has_team_constraint(match: dict[str, Any]) -> bool:
    return bool(match["teamId"])


def _has_roles_constraint(match: dict[str, Any]) -> bool:
    return bool(match["roles"])


def _matches_binding_scope(match: dict[str, Any], scope: dict[str, Any]) -> bool:
    peer_state = match["peer"]["state"]
    if peer_state == "invalid":
        return False
    if peer_state == "valid":
        scope_peer = scope.get("peer")
        if (
            not scope_peer
            or not peer_kind_matches(match["peer"]["kind"], scope_peer["kind"])
            or scope_peer["id"] != match["peer"]["id"]
        ):
            return False
    if peer_state == "wildcard-kind":
        scope_peer = scope.get("peer")
        if not scope_peer or not peer_kind_matches(match["peer"]["kind"], scope_peer["kind"]):
            return False
    return route_binding_scope_matches(match, scope)


def _collect_peer_indexed_bindings(
    index: dict[str, Any], peer: dict[str, Any] | None
) -> list[dict[str, Any]]:
    if not peer:
        return []
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for key in _peer_lookup_keys(peer["kind"], peer["id"]):
        matches = index["byPeer"].get(key)
        if not matches:
            continue
        for match in matches:
            match_id = id(match)
            if match_id in seen:
                continue
            seen.add(match_id)
            out.append(match)
    return out


def resolve_agent_route(input_cfg: dict[str, Any]) -> ResolvedAgentRoute:
    cfg = input_cfg.get("cfg")
    channel = _normalize_token(input_cfg.get("channel"))
    account_id = normalize_account_id(input_cfg.get("accountId"))
    input_peer = input_cfg.get("peer")
    peer = (
        {
            "kind": normalize_chat_type(input_peer.get("kind")) or input_peer.get("kind"),
            "id": _normalize_id(input_peer.get("id")),
        }
        if input_peer
        else None
    )
    guild_id = _normalize_id(input_cfg.get("guildId"))
    team_id = _normalize_id(input_cfg.get("teamId"))
    member_role_ids = input_cfg.get("memberRoleIds") or []
    member_role_id_set = set(member_role_ids)
    session_cfg = getattr(cfg, "session", None) if cfg else None
    dm_scope = session_cfg.get("dmScope", "main") if isinstance(session_cfg, dict) else "main"
    identity_links = session_cfg.get("identityLinks") if isinstance(session_cfg, dict) else None
    should_log_debug = _should_log_verbose()
    input_parent_peer = input_cfg.get("parentPeer")
    parent_peer = (
        {
            "kind": normalize_chat_type(input_parent_peer.get("kind")) or input_parent_peer.get("kind"),
            "id": _normalize_id(input_parent_peer.get("id")),
        }
        if input_parent_peer
        else None
    )

    route_cache = (
        None if (should_log_debug or identity_links) else _resolve_route_cache_for_config(cfg)
    )
    route_cache_key = ""
    if route_cache is not None:
        route_cache_key = _build_resolved_route_cache_key(
            {
                "channel": channel,
                "accountId": account_id,
                "peer": peer,
                "parentPeer": parent_peer,
                "guildId": guild_id,
                "teamId": team_id,
                "memberRoleIds": member_role_ids,
                "dmScope": dm_scope,
            }
        )
    if route_cache is not None and route_cache_key:
        cached_route = route_cache.get(route_cache_key)
        if cached_route:
            return {**cached_route}

    bindings = _get_evaluated_bindings_for_channel_account(cfg, channel, account_id)
    bindings_index = _get_evaluated_binding_index_for_channel_account(cfg, channel, account_id)

    def choose(
        agent_id: str,
        matched_by: MatchedBy,
        session_override: dict[str, Any] | None = None,
    ) -> ResolvedAgentRoute:
        resolved_agent_id = pick_first_existing_agent_id(cfg, agent_id)
        effective_dm_scope = (
            (session_override or {}).get("dmScope", dm_scope)
            if session_override
            else dm_scope
        )
        session_key = build_agent_session_key(
            {
                "agentId": resolved_agent_id,
                "channel": channel,
                "accountId": account_id,
                "peer": peer,
                "dmScope": effective_dm_scope,
                "identityLinks": identity_links,
            }
        )
        main_session_key = normalize_lowercase_string_or_empty(
            build_agent_main_session_key(
                {"agentId": resolved_agent_id, "mainKey": DEFAULT_MAIN_KEY}
            )
        )
        route: ResolvedAgentRoute = {
            "agentId": resolved_agent_id,
            "channel": channel,
            "accountId": account_id,
            "sessionKey": session_key,
            "mainSessionKey": main_session_key,
            "lastRoutePolicy": derive_last_route_policy(
                {"sessionKey": session_key, "mainSessionKey": main_session_key}
            ),
            "matchedBy": matched_by,
        }
        if route_cache is not None and route_cache_key:
            route_cache[route_cache_key] = route
            if len(route_cache) > _MAX_RESOLVED_ROUTE_CACHE_KEYS:
                route_cache.clear()
                route_cache[route_cache_key] = route
        return route

    def format_peer(value: dict[str, Any] | None) -> str:
        if value and value.get("kind") and value.get("id"):
            return f"{value['kind']}:{value['id']}"
        return "none"

    def format_normalized_peer(value: dict[str, Any]) -> str:
        state = value["state"]
        if state == "none":
            return "none"
        if state == "invalid":
            return "invalid"
        if state == "wildcard-kind":
            return f"{value['kind']}:*"
        return f"{value['kind']}:{value['id']}"

    if should_log_debug:
        _log_debug(
            f"[routing] resolveAgentRoute: channel={channel} accountId={account_id} peer={format_peer(peer)} guildId={guild_id or 'none'} teamId={team_id or 'none'} bindings={len(bindings)}"
        )
        for entry in bindings:
            _log_debug(
                f"[routing] binding: agentId={entry['binding'].get('agentId')} accountPattern={entry['match']['accountPattern'] or 'default'} peer={format_normalized_peer(entry['match']['peer'])} guildId={entry['match']['guildId'] or 'none'} teamId={entry['match']['teamId'] or 'none'} roles={len(entry['match']['roles']) if entry['match']['roles'] else 0}"
            )

    base_scope = {
        "guildId": guild_id,
        "teamId": team_id,
        "memberRoleIds": member_role_id_set,
    }

    def make_tier(
        matched_by: str,
        enabled: bool,
        scope_peer: dict[str, Any] | None,
        candidates: list[dict[str, Any]],
        predicate,
    ) -> dict[str, Any]:
        return {
            "matchedBy": matched_by,
            "enabled": enabled,
            "scopePeer": scope_peer,
            "candidates": candidates,
            "predicate": predicate,
        }

    tiers: list[dict[str, Any]] = [
        make_tier(
            "binding.peer",
            bool(peer),
            peer,
            _collect_peer_indexed_bindings(bindings_index, peer),
            lambda candidate: candidate["match"]["peer"]["state"] == "valid",
        ),
        make_tier(
            "binding.peer.parent",
            bool(parent_peer and parent_peer.get("id")),
            parent_peer if (parent_peer and parent_peer.get("id")) else None,
            _collect_peer_indexed_bindings(bindings_index, parent_peer),
            lambda candidate: candidate["match"]["peer"]["state"] == "valid",
        ),
        make_tier(
            "binding.peer.wildcard",
            bool(peer),
            peer,
            bindings_index["byPeerWildcard"],
            lambda candidate: candidate["match"]["peer"]["state"] == "wildcard-kind",
        ),
        make_tier(
            "binding.guild+roles",
            bool(guild_id and len(member_role_ids) > 0),
            peer,
            (bindings_index["byGuildWithRoles"].get(guild_id, []) if guild_id else []),
            lambda candidate: _has_guild_constraint(candidate["match"])
            and _has_roles_constraint(candidate["match"]),
        ),
        make_tier(
            "binding.guild",
            bool(guild_id),
            peer,
            (bindings_index["byGuild"].get(guild_id, []) if guild_id else []),
            lambda candidate: _has_guild_constraint(candidate["match"])
            and not _has_roles_constraint(candidate["match"]),
        ),
        make_tier(
            "binding.team",
            bool(team_id),
            peer,
            (bindings_index["byTeam"].get(team_id, []) if team_id else []),
            lambda candidate: _has_team_constraint(candidate["match"]),
        ),
        make_tier(
            "binding.account",
            True,
            peer,
            bindings_index["byAccount"],
            lambda candidate: candidate["match"]["accountPattern"] != "*",
        ),
        make_tier(
            "binding.channel",
            True,
            peer,
            bindings_index["byChannel"],
            lambda candidate: candidate["match"]["accountPattern"] == "*",
        ),
    ]

    for tier in tiers:
        if not tier["enabled"]:
            continue
        for candidate in tier["candidates"]:
            if tier["predicate"](candidate) and _matches_binding_scope(
                candidate["match"],
                {**base_scope, "peer": tier["scopePeer"]},
            ):
                if should_log_debug:
                    _log_debug(
                        f"[routing] match: matchedBy={tier['matchedBy']} agentId={candidate['binding'].get('agentId')}"
                    )
                return choose(
                    candidate["binding"].get("agentId"),
                    tier["matchedBy"],
                    candidate["binding"].get("session"),
                )

    return choose(_resolve_default_agent_id(cfg), "default")


__all__ = [
    "RoutePeerKind",
    "ResolveAgentRouteInput",
    "ResolvedAgentRoute",
    "derive_last_route_policy",
    "resolve_inbound_last_route_session_key",
    "build_agent_session_key",
    "pick_first_existing_agent_id",
    "resolve_agent_route",
]
