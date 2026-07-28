from __future__ import annotations

import re
from typing import Any

from openclaw.plugin_sdk.provider_model_shared import supports_claude_adaptive_thinking
from openclaw.plugin_sdk.string_coerce_runtime import normalize_optional_lowercase_string

CopilotRuntimeApi = str
CopilotReasoningCompat = dict[str, Any] | None

COPILOT_CHAT_COMPLETIONS_COMPAT: dict[str, Any] = {
    "supportsStore": False,
    "supportsDeveloperRole": False,
    "supportsUsageInStreaming": False,
    "maxTokensField": "max_tokens",
}

COPILOT_XHIGH_MODEL_IDS = {"gpt-5.4", "gpt-5.3-codex"}

STATIC_MODEL_OVERRIDES: dict[str, dict[str, Any]] = {
    "claude-opus-4.6-1m": {
        "name": "Claude Opus 4.6 (1M context)",
        "api": "anthropic-messages",
        "reasoning": True,
        "contextWindow": 1_000_000,
        "maxTokens": 64_000,
        "thinkingLevelMap": {"xhigh": None, "max": None},
        "compat": {"supportedReasoningEfforts": ["low", "medium", "high"]},
    },
    "claude-opus-4.7-1m-internal": {
        "name": "Claude Opus 4.7 (1M context)",
        "api": "anthropic-messages",
        "reasoning": True,
        "contextWindow": 1_000_000,
        "maxTokens": 64_000,
        "thinkingLevelMap": {"xhigh": "xhigh", "max": None},
        "compat": {"supportedReasoningEfforts": ["low", "medium", "high", "xhigh"]},
    },
    "gpt-5.5": {
        "name": "GPT-5.5",
        "reasoning": True,
        "contextWindow": 400_000,
        "maxTokens": 128_000,
    },
}


def _is_copilot_gemini_model_id(model_id: str) -> bool:
    return bool(re.search(r"(?:^|[-_.])gemini(?:$|[-_.])", model_id))


def _is_copilot_claude45_model_id(model_id: str) -> bool:
    return bool(re.search(r"^claude-(?:haiku|opus|sonnet)-4[.-]5(?:$|[-.])", model_id))


def resolve_copilot_transport_api(model_id: str) -> str:
    normalized = normalize_optional_lowercase_string(model_id) or ""
    if "claude" in normalized:
        return "anthropic-messages"
    if _is_copilot_gemini_model_id(normalized):
        return "openai-completions"
    return "openai-responses"


def resolve_copilot_model_compat(model_id: str) -> dict[str, Any] | None:
    normalized = normalize_optional_lowercase_string(model_id) or ""
    if _is_copilot_gemini_model_id(normalized):
        return dict(COPILOT_CHAT_COMPLETIONS_COMPAT)
    if _is_copilot_claude45_model_id(normalized):
        return {"supportsEagerToolInputStreaming": False}
    return None


def _compat_supports_effort(
    compat: CopilotReasoningCompat,
    effort: str,
) -> bool:
    efforts = compat.get("supportedReasoningEfforts") if compat else None
    if not isinstance(efforts, list):
        return False
    normalized_effort = normalize_optional_lowercase_string(effort)
    return any(
        normalize_optional_lowercase_string(candidate) == normalized_effort
        for candidate in efforts
    )


def resolve_copilot_extended_thinking_levels(
    model_id: str,
    compat: CopilotReasoningCompat = None,
) -> list[str]:
    normalized_model_id = normalize_optional_lowercase_string(model_id) or ""
    static_compat = resolve_static_copilot_model_override(normalized_model_id)
    if static_compat:
        static_compat = static_compat.get("compat")
    is_claude_model = "claude" in normalized_model_id
    supports_adaptive_claude_effort = (
        not is_claude_model
        or supports_claude_adaptive_thinking({"id": normalized_model_id})
    )
    levels: list[str] = []
    if (
        supports_adaptive_claude_effort
        and (
            normalized_model_id in COPILOT_XHIGH_MODEL_IDS
            or _compat_supports_effort(compat, "xhigh")
            or _compat_supports_effort(static_compat, "xhigh")
        )
    ):
        levels.append("xhigh")
    if (
        is_claude_model
        and supports_adaptive_claude_effort
        and (
            _compat_supports_effort(compat, "max")
            or _compat_supports_effort(static_compat, "max")
        )
    ):
        levels.append("max")
    return levels


def resolve_static_copilot_model_override(
    model_id: str,
) -> dict[str, Any] | None:
    normalized = normalize_optional_lowercase_string(model_id) or ""
    return STATIC_MODEL_OVERRIDES.get(normalized)
