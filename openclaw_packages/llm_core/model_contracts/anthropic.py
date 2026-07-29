import re
from typing import Any, Dict, Optional, TypedDict


class ClaudeModelRef(TypedDict, total=False):
    id: Optional[str]
    params: Optional[Dict[str, Any]]


class ClaudeEffortModelRef(ClaudeModelRef, total=False):
    thinkingLevelMap: Optional[Dict[str, Optional[str]]]


CLAUDE_FABLE_5_THINKING_PROFILE = {
    "levels": [
        {"id": "off"},
        {"id": "minimal"},
        {"id": "low"},
        {"id": "medium"},
        {"id": "high"},
        {"id": "xhigh"},
        {"id": "adaptive"},
        {"id": "max"},
    ],
    "defaultLevel": "high",
    "preserveWhenCatalogReasoningFalse": True,
}


def _normalize_claude_model_id(model_id: Optional[str]) -> str:
    normalized = (model_id or "").strip().lower()
    if normalized.startswith("anthropic/"):
        normalized = normalized[len("anthropic/"):]
    return re.sub(r"[._\s]+", "-", normalized)


def resolve_claude_model_identity(ref: ClaudeModelRef) -> str:
    params = ref.get("params") or {}
    configured_canonical_model_id = (
        params.get("canonicalModelId") if isinstance(params.get("canonicalModelId"), str) else None
    )
    normalized = _normalize_claude_model_id(configured_canonical_model_id or ref.get("id"))
    match = re.search(r"(?:^|[-/])claude-", normalized)
    if match:
        start = match.start()
        if match.group().startswith("claude-"):
            return normalized[start:]
        return normalized[start + 1:]
    return normalized


def resolve_claude_fable_5_model_identity(ref: ClaudeModelRef) -> Optional[str]:
    normalized = resolve_claude_model_identity(ref)
    match = re.search(r"(?:^|-)claude-fable-5(?=$|[^a-z0-9])", normalized)
    if not match:
        return None
    start = match.start()
    if match.group().startswith("-"):
        return normalized[start + 1:]
    return normalized[start:]


def supports_claude_adaptive_thinking(ref: ClaudeModelRef) -> bool:
    model_id = resolve_claude_model_identity(ref)
    return bool(
        re.search(
            r"(?:^|-)claude-(?:fable-5|mythos-preview|opus-4-(?:6|7|8)|sonnet-4-6)(?=$|[^a-z0-9])",
            model_id,
        )
    )


def supports_claude_native_max_effort(ref: ClaudeModelRef) -> bool:
    model_id = resolve_claude_model_identity(ref)
    return bool(
        re.search(
            r"(?:^|-)claude-(?:fable-5|opus-4-(?:6|7|8)|sonnet-4-6)(?=$|[^a-z0-9])",
            model_id,
        )
    )


def supports_claude_native_xhigh_effort(ref: ClaudeModelRef) -> bool:
    model_id = resolve_claude_model_identity(ref)
    return bool(
        re.search(
            r"(?:^|-)claude-(?:fable-5|opus-4-(?:7|8))(?=$|[^a-z0-9])",
            model_id,
        )
    )


def resolve_claude_native_thinking_level_map(
    ref: ClaudeEffortModelRef,
) -> Optional[Dict[str, Optional[str]]]:
    if ref.get("thinkingLevelMap") is not None:
        return ref.get("thinkingLevelMap")
    if not supports_claude_native_max_effort(ref):
        return None
    return {
        "xhigh": "xhigh" if supports_claude_native_xhigh_effort(ref) else None,
        "max": "max",
    }
