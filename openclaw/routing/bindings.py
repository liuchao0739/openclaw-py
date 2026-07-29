"""Routing binding helpers resolve configured channel and agent route bindings.

Mirrors src/routing/bindings.ts.
"""

from __future__ import annotations

from typing import Any

from openclaw.routing.binding_scope import (
    normalize_route_binding_channel_id,
    resolve_normalized_route_binding_match,
)
from openclaw.routing.session_key import normalize_agent_id


def _list_route_bindings(cfg: Any) -> list[Any]:
    bindings = getattr(cfg, "bindings", None) if cfg else None
    if isinstance(bindings, list):
        return bindings
    if isinstance(bindings, dict):
        result: list[Any] = []
        for value in bindings.values():
            if isinstance(value, list):
                result.extend(value)
            else:
                result.append(value)
        return result
    return []


def _resolve_default_agent_id(cfg: Any) -> str:
    agents = getattr(cfg, "agents", None) if cfg else None
    if agents and isinstance(agents, dict):
        default_id = agents.get("default")
        if isinstance(default_id, str) and default_id.strip():
            return default_id.strip()
    return "main"


def list_bindings(cfg: Any) -> list[Any]:
    return _list_route_bindings(cfg)


def list_bound_account_ids(cfg: Any, channel_id: str) -> list[str]:
    normalized_channel = normalize_route_binding_channel_id(channel_id)
    if not normalized_channel:
        return []
    ids: set[str] = set()
    for binding in list_bindings(cfg):
        resolved = resolve_normalized_route_binding_match(binding)
        if not resolved or resolved["channelId"] != normalized_channel:
            continue
        ids.add(resolved["accountId"])
    return sorted(ids)


def resolve_default_agent_bound_account_id(cfg: Any, channel_id: str) -> str | None:
    normalized_channel = normalize_route_binding_channel_id(channel_id)
    if not normalized_channel:
        return None
    default_agent_id = normalize_agent_id(_resolve_default_agent_id(cfg))
    for binding in list_bindings(cfg):
        resolved = resolve_normalized_route_binding_match(binding)
        if (
            not resolved
            or resolved["channelId"] != normalized_channel
            or resolved["agentId"] != default_agent_id
        ):
            continue
        return resolved["accountId"]
    return None


def build_channel_account_bindings(cfg: Any) -> dict[str, dict[str, list[str]]]:
    result: dict[str, dict[str, list[str]]] = {}
    for binding in list_bindings(cfg):
        resolved = resolve_normalized_route_binding_match(binding)
        if not resolved:
            continue
        by_agent = result.setdefault(resolved["channelId"], {})
        account_list = by_agent.setdefault(resolved["agentId"], [])
        if resolved["accountId"] not in account_list:
            account_list.append(resolved["accountId"])
    return result


def resolve_preferred_account_id(params: dict[str, Any]) -> str:
    bound_accounts = params.get("boundAccounts") or []
    if len(bound_accounts) > 0:
        return bound_accounts[0]
    return params.get("defaultAccountId", "")


__all__ = [
    "list_bindings",
    "list_bound_account_ids",
    "resolve_default_agent_bound_account_id",
    "build_channel_account_bindings",
    "resolve_preferred_account_id",
]
