"""Build usage contract from plugin hook reply usage state."""

from __future__ import annotations

from typing import Any


def build_usage_contract(
    state: dict[str, Any],
    surface: str | None = None,
) -> dict[str, Any]:
    """Build a structured usage contract from plugin hook reply usage state."""
    usage = state.get("usage") or {}
    input_tokens = usage.get("input")
    output_tokens = usage.get("output")
    cache_read = usage.get("cacheRead")
    cache_write = usage.get("cacheWrite")
    total = usage.get("total")

    has_split_tokens = input_tokens is not None or output_tokens is not None
    has_total_only_tokens = not has_split_tokens and total is not None
    has_tokens = (
        has_split_tokens
        or cache_read is not None
        or cache_write is not None
        or total is not None
    )

    prompt_total = (cache_read or 0) + (cache_write or 0) + (input_tokens or 0)
    cache_hit_pct = (
        round((cache_read or 0) / prompt_total * 100) if prompt_total > 0 else None
    )

    last = state.get("lastUsage")
    last_prompt_total = (
        (last.get("cacheRead") or 0) + (last.get("cacheWrite") or 0) + (last.get("input") or 0)
        if last
        else 0
    )
    last_cache_hit_pct = (
        round((last.get("cacheRead") or 0) / last_prompt_total * 100)
        if last and last_prompt_total > 0
        else None
    )

    max_tokens = state.get("contextTokenBudget")
    used_tokens = (
        state["contextUsedTokens"]
        if isinstance(state.get("contextUsedTokens"), (int, float)) and state["contextUsedTokens"] > 0
        else prompt_total if prompt_total > 0 else None
    )
    pct_used = (
        round(used_tokens / max_tokens * 100)
        if max_tokens and used_tokens is not None
        else None
    )

    override_source = state.get("overrideSource") or None
    is_override = (
        isinstance(state.get("overrideSource"), str)
        and state["overrideSource"] != ""
        and state["overrideSource"] != "auto"
    )

    return {
        "schema": "openclaw.usageLine.v1",
        "surface": surface,
        "agentId": state.get("agentId"),
        "chat_type": state.get("chatType"),
        "model": {
            "id": state.get("model"),
            "display_name": state.get("model"),
            "provider": state.get("provider"),
            "reasoning": state.get("reasoningEffort"),
            "actual": state.get("resolvedRef"),
            "resolved_ref": state.get("resolvedRef"),
            "requested": state.get("requested"),
            "is_fallback": state.get("fallbackUsed") is True,
            "is_override": is_override,
            "override_source": override_source,
            "auth_mode": state.get("authMode"),
        },
        "state": {
            "fast_mode": state.get("fastMode") if isinstance(state.get("fastMode"), bool) else None,
            "compactions": state.get("compactionCount") if isinstance(state.get("compactionCount"), (int, float)) else None,
        },
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read,
            "cache_write_tokens": cache_write,
            "total_tokens": total,
            "cache_hit_pct": cache_hit_pct,
            "has_tokens": has_tokens,
            "has_split_tokens": has_split_tokens,
            "has_total_only_tokens": has_total_only_tokens,
            "last": {
                "input_tokens": last.get("input"),
                "output_tokens": last.get("output"),
                "cache_read_tokens": last.get("cacheRead"),
                "cache_write_tokens": last.get("cacheWrite"),
                "total_tokens": last.get("total"),
                "cache_hit_pct": last_cache_hit_pct,
            } if last else None,
        },
        "context": {
            "used_tokens": used_tokens,
            "max_tokens": max_tokens,
            "pct_used": pct_used,
        },
        "cost": {
            "turn_usd": state.get("turnUsd") if isinstance(state.get("turnUsd"), (int, float)) else None,
            "available": isinstance(state.get("turnUsd"), (int, float)),
        },
        "timing": {
            "duration_ms": state.get("durationMs") if isinstance(state.get("durationMs"), (int, float)) else None,
        },
        "identity": {
            "name": state.get("identity", {}).get("name") if isinstance(state.get("identity"), dict) else None,
            "emoji": state.get("identity", {}).get("emoji") if isinstance(state.get("identity"), dict) else None,
            "avatar": state.get("identity", {}).get("avatar") if isinstance(state.get("identity"), dict) else None,
        },
        "session": {"id": state.get("sessionId")},
    }
