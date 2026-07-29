"""Routing session key helpers build stable session keys from route targets.

Mirrors src/routing/session-key.ts.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty
from openclaw.routing.account_id import (
    DEFAULT_ACCOUNT_ID,
    normalize_account_id,
    normalize_optional_account_id,
)

DEFAULT_AGENT_ID = "main"
DEFAULT_MAIN_KEY = "main"
SessionKeyShape = Literal["missing", "agent", "legacy_or_alias", "malformed_agent"]

_VALID_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$", re.IGNORECASE)
_INVALID_CHARS_RE = re.compile(r"[^a-z0-9_-]+")
_LEADING_DASH_RE = re.compile(r"^-+")
_TRAILING_DASH_RE = re.compile(r"-+$")

_AGENT_SESSION_KEY_RE = re.compile(r"^agent:([a-z0-9][a-z0-9_-]{0,63}):(.+)$", re.IGNORECASE)


def _normalize_token(value: str | None) -> str:
    return normalize_lowercase_string_or_empty(value)


def parse_agent_session_key(session_key: str | None) -> dict[str, str] | None:
    raw = (session_key or "").strip()
    if not raw:
        return None
    match = _AGENT_SESSION_KEY_RE.match(raw)
    if not match:
        return None
    return {"agentId": match.group(1), "rest": match.group(2)}


def is_cron_run_session_key(session_key: str | None) -> bool:
    parsed = parse_agent_session_key(session_key)
    if not parsed:
        return False
    return parsed["rest"].startswith("cron:")


def is_cron_session_key(session_key: str | None) -> bool:
    return is_cron_run_session_key(session_key)


def is_acp_session_key(session_key: str | None) -> bool:
    parsed = parse_agent_session_key(session_key)
    if not parsed:
        return False
    return parsed["rest"].startswith("acp:")


def is_subagent_session_key(session_key: str | None) -> bool:
    parsed = parse_agent_session_key(session_key)
    if not parsed:
        return False
    return parsed["rest"].startswith("subagent:")


def get_subagent_depth(session_key: str | None) -> int:
    parsed = parse_agent_session_key(session_key)
    if not parsed:
        return 0
    rest = parsed["rest"]
    if not rest.startswith("subagent:"):
        return 0
    parts = rest.split(":")
    if len(parts) < 2:
        return 0
    try:
        return int(parts[1])
    except ValueError:
        return 0


def parse_thread_session_suffix(session_key: str | None) -> str | None:
    parsed = parse_agent_session_key(session_key)
    if not parsed:
        return None
    rest = parsed["rest"]
    marker = ":thread:"
    idx = rest.find(marker)
    if idx < 0:
        return None
    return rest[idx + len(marker):]


def normalize_main_key(value: str | None) -> str:
    return _normalize_token(value) or DEFAULT_MAIN_KEY


def normalize_agent_id(value: str | None) -> str:
    trimmed = (value or "").strip()
    if not trimmed:
        return DEFAULT_AGENT_ID
    normalized = normalize_lowercase_string_or_empty(trimmed)
    if _VALID_ID_RE.match(trimmed):
        return normalized
    return (
        _INVALID_CHARS_RE.sub("-", normalized)
        .lstrip("-")
        .rstrip("-")[:64]
        or DEFAULT_AGENT_ID
    )


def normalize_optional_agent_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return normalize_agent_id(trimmed) if trimmed else None
    return None


def is_valid_agent_id(value: str | None) -> bool:
    trimmed = (value or "").strip()
    return bool(trimmed) and bool(_VALID_ID_RE.match(trimmed))


def sanitize_agent_id(value: str | None) -> str:
    return normalize_agent_id(value)


def build_agent_main_session_key(params: dict[str, Any]) -> str:
    agent_id = normalize_agent_id(params.get("agentId"))
    main_key = normalize_main_key(params.get("mainKey"))
    return f"agent:{agent_id}:{main_key}"


def _resolve_linked_peer_id(params: dict[str, Any]) -> str | None:
    identity_links = params.get("identityLinks")
    if not identity_links:
        return None
    peer_id = (params.get("peerId") or "").strip()
    if not peer_id:
        return None
    candidates: set[str] = set()
    raw_candidate = _normalize_token(peer_id)
    if raw_candidate:
        candidates.add(raw_candidate)
    channel = _normalize_token(params.get("channel"))
    if channel:
        scoped_candidate = _normalize_token(f"{channel}:{peer_id}")
        if scoped_candidate:
            candidates.add(scoped_candidate)
    if not candidates:
        return None
    for canonical, ids in identity_links.items():
        canonical_name = canonical.strip() if isinstance(canonical, str) else ""
        if not canonical_name:
            continue
        if not isinstance(ids, list):
            continue
        for identity_id in ids:
            normalized = _normalize_token(identity_id)
            if normalized and normalized in candidates:
                return canonical_name
    return None


def _normalize_session_peer_id(params: dict[str, Any]) -> str:
    peer_id = (params.get("peerId") or "").strip()
    if not peer_id:
        return ""
    return _normalize_token(peer_id)


def build_agent_peer_session_key(params: dict[str, Any]) -> str:
    peer_kind = params.get("peerKind") or "direct"
    if peer_kind == "direct":
        dm_scope = params.get("dmScope") or "main"
        peer_id = (params.get("peerId") or "").strip()
        linked_peer_id = (
            None
            if dm_scope == "main"
            else _resolve_linked_peer_id(
                {
                    "identityLinks": params.get("identityLinks"),
                    "channel": params.get("channel"),
                    "peerId": peer_id,
                }
            )
        )
        if linked_peer_id:
            peer_id = linked_peer_id
        peer_id = _normalize_token(peer_id)
        if dm_scope == "per-account-channel-peer" and peer_id:
            channel = _normalize_token(params.get("channel")) or "unknown"
            account_id = normalize_account_id(params.get("accountId"))
            return f"agent:{normalize_agent_id(params.get('agentId'))}:{channel}:{account_id}:direct:{peer_id}"
        if dm_scope == "per-channel-peer" and peer_id:
            channel = _normalize_token(params.get("channel")) or "unknown"
            return f"agent:{normalize_agent_id(params.get('agentId'))}:{channel}:direct:{peer_id}"
        if dm_scope == "per-peer" and peer_id:
            return f"agent:{normalize_agent_id(params.get('agentId'))}:direct:{peer_id}"
        return build_agent_main_session_key(
            {"agentId": params.get("agentId"), "mainKey": params.get("mainKey")}
        )
    channel = _normalize_token(params.get("channel")) or "unknown"
    peer_id = _normalize_session_peer_id(
        {"channel": params.get("channel"), "peerKind": peer_kind, "peerId": params.get("peerId")}
    ) or "unknown"
    return f"agent:{normalize_agent_id(params.get('agentId'))}:{channel}:{peer_kind}:{peer_id}"


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
            "peerId": _normalize_token((peer or {}).get("id")) or "unknown" if peer else None,
            "dmScope": params.get("dmScope"),
            "identityLinks": params.get("identityLinks"),
        }
    )


def to_agent_request_session_key(store_key: str | None) -> str | None:
    raw = (store_key or "").strip()
    if not raw:
        return None
    parsed = parse_agent_session_key(raw)
    return parsed["rest"] if parsed else raw


def agent_session_keys_match_by_request_key(
    left: str | None, right: str | None
) -> bool:
    left_raw = (left or "").strip()
    right_raw = (right or "").strip()
    if not left_raw or not right_raw:
        return False
    return (
        left_raw == right_raw
        or to_agent_request_session_key(left_raw) == to_agent_request_session_key(right_raw)
    )


def to_agent_store_session_key(params: dict[str, Any]) -> str:
    raw = (params.get("requestKey") or "").strip()
    lowered = _normalize_token(raw)
    if not raw or lowered == DEFAULT_MAIN_KEY:
        return build_agent_main_session_key(
            {"agentId": params.get("agentId"), "mainKey": params.get("mainKey")}
        )
    parsed = parse_agent_session_key(raw)
    if parsed:
        return f"agent:{parsed['agentId']}:{parsed['rest']}"
    if lowered.startswith("agent:"):
        return lowered
    return f"agent:{normalize_agent_id(params.get('agentId'))}:{lowered}"


def resolve_agent_id_from_session_key(session_key: str | None) -> str:
    parsed = parse_agent_session_key(session_key)
    return normalize_agent_id(parsed["agentId"] if parsed else DEFAULT_AGENT_ID)


def classify_session_key_shape(session_key: str | None) -> SessionKeyShape:
    raw = (session_key or "").strip()
    if not raw:
        return "missing"
    if parse_agent_session_key(raw):
        return "agent"
    lowered = _normalize_token(raw)
    return "malformed_agent" if lowered.startswith("agent:") else "legacy_or_alias"


def is_unscoped_session_key_sentinel(session_key: str | None) -> bool:
    lowered = _normalize_token(session_key)
    return lowered == "global" or lowered == "unknown"


def scope_legacy_session_key_to_agent(params: dict[str, Any]) -> str | None:
    raw = (params.get("sessionKey") or "").strip()
    if not raw:
        return None
    agent_id = (params.get("agentId") or "").strip()
    if not agent_id or classify_session_key_shape(raw) != "legacy_or_alias":
        return raw
    return to_agent_store_session_key(
        {
            "agentId": agent_id,
            "requestKey": raw,
            "mainKey": params.get("mainKey"),
        }
    )


def scoped_heartbeat_wake_options(
    session_key: str,
    wake_options: dict[str, Any],
    main_key: str | None = None,
    scope: str | None = None,
) -> dict[str, Any]:
    parsed = parse_agent_session_key(session_key)
    if not parsed:
        return wake_options
    if is_cron_run_session_key(session_key):
        if scope == "global":
            return {**wake_options, "agentId": parsed["agentId"]}
        return {
            **wake_options,
            "sessionKey": build_agent_main_session_key(
                {"agentId": parsed["agentId"], "mainKey": main_key}
            ),
        }
    return {**wake_options, "sessionKey": session_key}


def resolve_event_session_key(
    session_key: str,
    main_key: str | None = None,
    scope: str | None = None,
) -> str:
    parsed = parse_agent_session_key(session_key)
    if not parsed or not is_cron_run_session_key(session_key):
        return session_key
    if scope == "global":
        return "global"
    return build_agent_main_session_key({"agentId": parsed["agentId"], "mainKey": main_key})


def build_group_history_key(params: dict[str, Any]) -> str:
    channel = _normalize_token(params.get("channel")) or "unknown"
    account_id = normalize_account_id(params.get("accountId"))
    peer_id = _normalize_session_peer_id(
        {
            "channel": channel,
            "peerKind": params.get("peerKind"),
            "peerId": params.get("peerId"),
        }
    ) or "unknown"
    return f"{channel}:{account_id}:{params.get('peerKind')}:{peer_id}"


def resolve_thread_session_keys(params: dict[str, Any]) -> dict[str, Any]:
    thread_id = (params.get("threadId") or "").strip()
    if not thread_id:
        return {
            "sessionKey": params.get("baseSessionKey"),
            "parentSessionKey": None,
        }
    normalize_thread_id = params.get("normalizeThreadId")
    normalized_thread = (
        normalize_thread_id(thread_id)
        if normalize_thread_id
        else _normalize_token(thread_id)
    )
    use_suffix = params.get("useSuffix")
    use_suffix = True if use_suffix is None else use_suffix
    session_key = (
        f"{params.get('baseSessionKey')}:thread:{normalized_thread}"
        if use_suffix
        else params.get("baseSessionKey")
    )
    return {
        "sessionKey": session_key,
        "parentSessionKey": params.get("parentSessionKey"),
    }


__all__ = [
    "DEFAULT_AGENT_ID",
    "DEFAULT_MAIN_KEY",
    "DEFAULT_ACCOUNT_ID",
    "SessionKeyShape",
    "build_agent_main_session_key",
    "build_agent_peer_session_key",
    "build_agent_session_key",
    "build_group_history_key",
    "classify_session_key_shape",
    "get_subagent_depth",
    "is_acp_session_key",
    "is_cron_run_session_key",
    "is_cron_session_key",
    "is_subagent_session_key",
    "is_unscoped_session_key_sentinel",
    "is_valid_agent_id",
    "normalize_account_id",
    "normalize_agent_id",
    "normalize_main_key",
    "normalize_optional_account_id",
    "normalize_optional_agent_id",
    "parse_agent_session_key",
    "parse_thread_session_suffix",
    "resolve_agent_id_from_session_key",
    "resolve_event_session_key",
    "resolve_linked_peer_id",
    "resolve_thread_session_keys",
    "sanitize_agent_id",
    "scope_legacy_session_key_to_agent",
    "scoped_heartbeat_wake_options",
    "to_agent_request_session_key",
    "to_agent_store_session_key",
    "agent_session_keys_match_by_request_key",
]
