"""Claude model identity and effort helpers.

Mirrors packages/llm-core/src/model-contracts/anthropic.ts.
"""

from __future__ import annotations

import re
from typing import Any, TypedDict


class ClaudeModelRef(TypedDict, total=False):
    id: str
    params: dict[str, Any]


class ClaudeEffortModelRef(ClaudeModelRef, total=False):
    thinkingLevelMap: dict[str, str | None]


CLAUDE_FABLE_5_THINKING_PROFILE: dict[str, Any] = {
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


def _normalize_claude_model_id(model_id: str | None) -> str:
    normalized = (model_id or "").strip().lower()
    unprefixed = normalized.removeprefix("anthropic/")
    return re.sub(r"[._\s]+", "-", unprefixed)


def resolve_claude_model_identity(ref: ClaudeModelRef | dict[str, Any] | Any) -> str:
    """Resolve the canonical normalized Claude model id for one runtime model ref."""
    if isinstance(ref, dict):
        params = ref.get("params") if isinstance(ref.get("params"), dict) else {}
        configured = params.get("canonicalModelId")
        model_id = ref.get("id")
    else:
        params = getattr(ref, "params", None)
        configured = params.get("canonicalModelId") if isinstance(params, dict) else None
        model_id = getattr(ref, "id", None)

    normalized = _normalize_claude_model_id(
        configured if isinstance(configured, str) else str(model_id or "")
    )
    match = re.search(r"(?:^|[-/])claude-", normalized)
    if not match:
        return normalized
    start = match.start()
    if match.group(0).startswith("claude-"):
        return normalized[start:]
    return normalized[start + 1 :]


def resolve_claude_fable5_model_identity(
    ref: ClaudeModelRef | dict[str, Any] | Any,
) -> str | None:
    """Resolve Claude Fable 5 through direct ids, cloud ids, or deployment metadata."""
    normalized = resolve_claude_model_identity(ref)
    match = re.search(r"(?:^|-)claude-fable-5(?=$|[^a-z0-9])", normalized)
    if not match:
        return None
    start = match.start()
    if match.group(0).startswith("-"):
        return normalized[start + 1 :]
    return normalized[start:]


def supports_claude_adaptive_thinking(ref: ClaudeModelRef | dict[str, Any] | Any) -> bool:
    """Return whether a Claude model supports adaptive thinking."""
    model_id = resolve_claude_model_identity(ref)
    return bool(
        re.search(
            r"(?:^|-)claude-(?:fable-5|mythos-preview|opus-4-(?:6|7|8)|sonnet-4-6)(?=$|[^a-z0-9])",
            model_id,
        )
    )


def supports_claude_native_max_effort(ref: ClaudeModelRef | dict[str, Any] | Any) -> bool:
    """Return whether a Claude model supports native max effort."""
    model_id = resolve_claude_model_identity(ref)
    return bool(
        re.search(
            r"(?:^|-)claude-(?:fable-5|opus-4-(?:6|7|8)|sonnet-4-6)(?=$|[^a-z0-9])",
            model_id,
        )
    )


def supports_claude_native_xhigh_effort(ref: ClaudeModelRef | dict[str, Any] | Any) -> bool:
    """Return whether a Claude model supports native xhigh effort."""
    model_id = resolve_claude_model_identity(ref)
    return bool(
        re.search(r"(?:^|-)claude-(?:fable-5|opus-4-(?:7|8))(?=$|[^a-z0-9])", model_id)
    )


def resolve_claude_native_thinking_level_map(
    ref: ClaudeEffortModelRef | dict[str, Any] | Any,
) -> dict[str, str | None] | None:
    """Fill native Claude effort mappings when no route-specific contract was published."""
    if isinstance(ref, dict):
        thinking_level_map = ref.get("thinkingLevelMap")
    else:
        thinking_level_map = getattr(ref, "thinkingLevelMap", None)

    if thinking_level_map is not None:
        return thinking_level_map if isinstance(thinking_level_map, dict) else None
    if not supports_claude_native_max_effort(ref):
        return None
    return {
        "xhigh": "xhigh" if supports_claude_native_xhigh_effort(ref) else None,
        "max": "max",
    }


__all__ = [
    "CLAUDE_FABLE_5_THINKING_PROFILE",
    "ClaudeEffortModelRef",
    "ClaudeModelRef",
    "resolve_claude_fable5_model_identity",
    "resolve_claude_model_identity",
    "resolve_claude_native_thinking_level_map",
    "supports_claude_adaptive_thinking",
    "supports_claude_native_max_effort",
    "supports_claude_native_xhigh_effort",
]
