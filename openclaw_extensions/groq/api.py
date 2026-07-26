"""Groq API module exposes the plugin public contract."""

from __future__ import annotations

from typing import Any

GROQ_QWEN3_32B_ID = "qwen/qwen3-32b"
GROQ_GPT_OSS_REASONING_IDS = {
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-safeguard-20b",
}

GROQ_QWEN_REASONING_EFFORTS = ("none", "default")
GROQ_GPT_OSS_REASONING_EFFORTS = ("low", "medium", "high")

GROQ_QWEN_REASONING_EFFORT_MAP = {
    "off": "none",
    "none": "none",
    "minimal": "default",
    "low": "default",
    "medium": "default",
    "high": "default",
    "xhigh": "default",
    "adaptive": "default",
    "max": "default",
}


def _normalize_groq_model_id(model_id: str | None) -> str:
    return model_id.strip().lower() if isinstance(model_id, str) else ""


def resolve_groq_reasoning_compat_patch(
    model_id: str,
) -> dict[str, Any] | None:
    """Return Groq-native reasoning effort compatibility for supported models."""
    normalized = _normalize_groq_model_id(model_id)
    if normalized == GROQ_QWEN3_32B_ID:
        return {
            "supportsReasoningEffort": True,
            "supportedReasoningEfforts": list(GROQ_QWEN_REASONING_EFFORTS),
            "reasoningEffortMap": dict(GROQ_QWEN_REASONING_EFFORT_MAP),
        }
    if normalized in GROQ_GPT_OSS_REASONING_IDS:
        return {
            "supportsReasoningEffort": True,
            "supportedReasoningEfforts": list(GROQ_GPT_OSS_REASONING_EFFORTS),
        }
    return None
