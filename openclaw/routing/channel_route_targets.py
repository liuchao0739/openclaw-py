"""Channel route target helpers normalize channel route targets for delivery.

Mirrors src/routing/channel-route-targets.ts.
"""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core.record_coerce import is_record
from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty
from openclaw.channels.ids import normalize_chat_channel_id
from openclaw.routing.resolve_route import resolve_agent_route
from openclaw.routing.session_key import (
    DEFAULT_ACCOUNT_ID,
    normalize_account_id,
    normalize_agent_id,
)

_CHANNELS_CONFIG_META_KEYS = {"defaults", "modelByChannel"}


def _normalize_configured_channel_key(raw: str | None = None) -> str:
    return normalize_chat_channel_id(raw) or normalize_lowercase_string_or_empty(raw)


def _normalize_route_binding_channel_key(raw: str | None = None) -> str:
    return normalize_lowercase_string_or_empty(raw)


def _list_configured_channel_ids(cfg: Any) -> list[str]:
    channels = getattr(cfg, "channels", None) if cfg else None
    if not is_record(channels):
        return []
    result: list[str] = []
    for channel_id, value in channels.items():
        if channel_id in _CHANNELS_CONFIG_META_KEYS:
            continue
        if is_record(value) and value.get("enabled") is False:
            continue
        normalized = _normalize_configured_channel_key(channel_id)
        if normalized:
            result.append(normalized)
    return sorted(result)


def _list_configured_channel_account_ids(cfg: Any, channel_id: str) -> list[str]:
    channels = getattr(cfg, "channels", None) if cfg else None
    if not is_record(channels):
        return []
    channel = None
    for cid, value in channels.items():
        if _normalize_configured_channel_key(cid) == channel_id:
            channel = value
            break
    if not is_record(channel) or not is_record(channel.get("accounts")):
        return []
    result: list[str] = []
    for account_id, value in channel["accounts"].items():
        if is_record(value) and value.get("enabled") is False:
            continue
        normalized = normalize_account_id(account_id)
        if normalized:
            result.append(normalized)
    return sorted(result)


def _add_target(by_agent: dict[str, set[str]], agent_id: str, channel: str) -> None:
    normalized_agent_id = normalize_agent_id(agent_id)
    trimmed_channel = channel.strip()
    if not normalized_agent_id or not trimmed_channel:
        return
    channels = by_agent.setdefault(normalized_agent_id, set())
    channels.add(trimmed_channel)


def collect_channel_route_targets(cfg: Any) -> list[dict[str, Any]]:
    by_agent: dict[str, set[str]] = {}
    from openclaw.routing.bindings import list_bindings

    for binding in list_bindings(cfg):
        match_obj = binding.get("match") if isinstance(binding, dict) else None
        channel = (
            _normalize_route_binding_channel_key(match_obj.get("channel"))
            if isinstance(match_obj, dict)
            else ""
        )
        _add_target(by_agent, binding.get("agentId"), channel)

    for channel in _list_configured_channel_ids(cfg):
        account_ids = _list_configured_channel_account_ids(cfg, channel)
        sampled_account_ids = account_ids if len(account_ids) > 0 else [DEFAULT_ACCOUNT_ID]
        for account_id in sampled_account_ids:
            route = resolve_agent_route({"cfg": cfg, "channel": channel, "accountId": account_id})
            _add_target(by_agent, route["agentId"], channel)

    result: list[dict[str, Any]] = []
    for agent_id, channels in by_agent.items():
        sorted_channels = sorted(channels)
        if len(sorted_channels) > 0:
            result.append({"agentId": agent_id, "channels": sorted_channels})
    return sorted(result, key=lambda target: target["agentId"])


__all__ = [
    "collect_channel_route_targets",
]
