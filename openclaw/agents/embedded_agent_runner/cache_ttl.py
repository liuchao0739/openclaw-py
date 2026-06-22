"""Cache-TTL eligibility and session markers for prompt-cache retention."""

from __future__ import annotations

from typing import Any, TypedDict

from openclaw.agents.embedded_agent_runner.prompt_cache_retention import (
    is_google_prompt_cache_eligible,
)

CACHE_TTL_CUSTOM_TYPE = "openclaw.cache-ttl"


class CacheTtlContext(TypedDict, total=False):
    provider: str
    modelId: str


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _is_anthropic_family_cache_ttl(provider: str, model_id: str, model_api: str | None) -> bool:
    p = _norm(provider)
    if p in ("anthropic", "claude", "openrouter"):
        return True
    if model_api == "anthropic-messages":
        return True
    mid = _norm(model_id)
    return mid.startswith("claude-") or "anthropic" in mid


def is_cache_ttl_eligible_provider(
    provider: str,
    model_id: str,
    model_api: str | None = None,
) -> bool:
    p = _norm(provider)
    mid = _norm(model_id)
    if _is_anthropic_family_cache_ttl(p, mid, model_api):
        return True
    if p == "kilocode" and mid.startswith("claude-"):
        return True
    return is_google_prompt_cache_eligible(model_api=model_api, model_id=mid)


def _matches_context(data: dict[str, Any] | None, context: CacheTtlContext | None) -> bool:
    if not context:
        return True
    if context.get("provider") and _norm(data.get("provider")) != _norm(context.get("provider")):
        return False
    if context.get("modelId") and _norm(data.get("modelId")) != _norm(context.get("modelId")):
        return False
    return True


def read_last_cache_ttl_timestamp(
    session_manager: object | None,
    context: CacheTtlContext | None = None,
) -> int | None:
    get_entries = getattr(session_manager, "get_entries", None)
    if not callable(get_entries):
        sm = session_manager if isinstance(session_manager, dict) else None
        if sm and callable(sm.get("getEntries")):
            get_entries = sm["getEntries"]
        else:
            return None
    try:
        entries = get_entries()
    except (TypeError, AttributeError):
        return None
    if not isinstance(entries, list):
        return None
    for entry in reversed(entries):
        if not isinstance(entry, dict):
            continue
        if entry.get("type") != "custom" or entry.get("customType") != CACHE_TTL_CUSTOM_TYPE:
            continue
        data = entry.get("data")
        if not isinstance(data, dict) or not _matches_context(data, context):
            continue
        ts = data.get("timestamp")
        if isinstance(ts, (int, float)) and ts == ts:
            return int(ts)
    return None