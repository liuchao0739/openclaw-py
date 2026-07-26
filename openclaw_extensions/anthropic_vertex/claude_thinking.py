"""Claude thinking profile resolution mirrored from provider-claude-thinking.ts."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.anthropic_vertex.claude_contracts import (
    CLAUDE_FABLE_5_THINKING_PROFILE,
    resolve_claude_fable5_model_identity,
    resolve_claude_model_identity,
    supports_claude_adaptive_thinking,
    supports_claude_native_xhigh_effort,
)

_BASE_CLAUDE_THINKING_LEVELS = [
    {"id": "off"},
    {"id": "minimal"},
    {"id": "low"},
    {"id": "medium"},
    {"id": "high"},
]


def is_claude_adaptive_thinking_default_model_id(model_id: str) -> bool:
    ref = {"id": model_id}
    return supports_claude_adaptive_thinking(ref) and not supports_claude_native_xhigh_effort(ref)


def resolve_claude_thinking_profile(
    model_id: str,
    params: dict[str, Any] | None = None,
    *,
    include_native_max: bool = False,
) -> dict[str, Any]:
    ref: dict[str, Any] = {"id": model_id}
    if params is not None:
        ref["params"] = params
    canonical_model_id = resolve_claude_model_identity(ref)
    if resolve_claude_fable5_model_identity(ref):
        return dict(CLAUDE_FABLE_5_THINKING_PROFILE)
    if supports_claude_native_xhigh_effort(ref):
        return {
            "levels": [
                * _BASE_CLAUDE_THINKING_LEVELS,
                {"id": "xhigh"},
                {"id": "adaptive"},
                {"id": "max"},
            ],
            "defaultLevel": "off",
        }
    if is_claude_adaptive_thinking_default_model_id(canonical_model_id):
        levels: list[dict[str, str]] = [
            *_BASE_CLAUDE_THINKING_LEVELS,
            {"id": "adaptive"},
        ]
        if include_native_max:
            levels.append({"id": "max"})
        return {
            "levels": levels,
            "defaultLevel": "adaptive",
        }
    return {"levels": list(_BASE_CLAUDE_THINKING_LEVELS)}
