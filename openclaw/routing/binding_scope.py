"""Binding scope helpers normalize route binding scope values.

Mirrors src/routing/binding-scope.ts.
"""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty
from openclaw.channels.ids import normalize_chat_channel_id
from openclaw.routing.session_key import normalize_account_id, normalize_agent_id


def normalize_route_binding_id(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value).strip()
    return ""


def normalize_route_binding_roles(value: list[str] | None) -> list[str] | None:
    return value if (isinstance(value, list) and len(value) > 0) else None


def normalize_route_binding_channel_id(raw: str | None = None) -> str | None:
    normalized = normalize_chat_channel_id(raw)
    if normalized:
        return normalized
    fallback = normalize_lowercase_string_or_empty(raw)
    return fallback or None


def resolve_normalized_route_binding_match(binding: dict[str, Any]) -> dict[str, str] | None:
    if not binding or not isinstance(binding, dict):
        return None
    match = binding.get("match")
    if not match or not isinstance(match, dict):
        return None
    channel_id = normalize_route_binding_channel_id(match.get("channel"))
    if not channel_id:
        return None
    account_id = match.get("accountId")
    account_id = account_id.strip() if isinstance(account_id, str) else ""
    if not account_id or account_id == "*":
        return None
    return {
        "agentId": normalize_agent_id(binding.get("agentId")),
        "accountId": normalize_account_id(account_id),
        "channelId": channel_id,
    }


def _scope_id_matches(constraint: str | None, exact: str, group_space: str) -> bool:
    if not constraint:
        return True
    return constraint == exact or constraint == group_space


def _has_role_lookup(member_role_ids: Any) -> bool:
    return hasattr(member_role_ids, "has") and callable(getattr(member_role_ids, "has"))


def _has_any_route_binding_role(
    roles: list[str], member_role_ids: Any
) -> bool:
    if not member_role_ids:
        return False
    if _has_role_lookup(member_role_ids):
        return any(member_role_ids.has(role) for role in roles)
    member_role_id_set = set(member_role_ids)
    return any(role in member_role_id_set for role in roles)


def route_binding_scope_matches(constraint: dict[str, Any], scope: dict[str, Any]) -> bool:
    guild_id = normalize_route_binding_id(scope.get("guildId"))
    team_id = normalize_route_binding_id(scope.get("teamId"))
    group_space = normalize_route_binding_id(scope.get("groupSpace"))
    if not _scope_id_matches(constraint.get("guildId"), guild_id, group_space):
        return False
    if not _scope_id_matches(constraint.get("teamId"), team_id, group_space):
        return False
    roles = normalize_route_binding_roles(constraint.get("roles"))
    if not roles:
        return True
    return _has_any_route_binding_role(roles, scope.get("memberRoleIds"))


__all__ = [
    "normalize_route_binding_id",
    "normalize_route_binding_roles",
    "normalize_route_binding_channel_id",
    "resolve_normalized_route_binding_match",
    "route_binding_scope_matches",
]
