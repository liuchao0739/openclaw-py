from __future__ import annotations

import re
from typing import Any

from openclaw.plugin_sdk.provider_model_shared import (
    resolve_claude_fable5_model_identity,
    resolve_claude_model_identity,
)

_BASE_CLAUDE_THINKING_LEVELS = [
    {"id": "off"},
    {"id": "minimal"},
    {"id": "low"},
    {"id": "medium"},
    {"id": "high"},
]


def _is_opus48_bedrock_model_ref(model_ref: str) -> bool:
    return bool(
        re.search(
            r"(?:^|[/.:])(?:(?:us|eu|ap|apac|au|jp|global)\.)?(?:anthropic\.)?claude-opus-4[.-]8(?:$|[-.:/])",
            model_ref,
            re.IGNORECASE,
        )
    )


def _is_opus46_bedrock_model_ref(model_ref: str) -> bool:
    return bool(
        re.search(
            r"(?:^|[/.:])(?:(?:us|eu|ap|apac|au|jp|global)\.)?(?:anthropic\.)?claude-opus-4[.-]6(?:$|[-.:/])",
            model_ref,
            re.IGNORECASE,
        )
    )


def is_opus47_bedrock_model_ref(model_ref: str) -> bool:
    return bool(
        re.search(
            r"(?:^|[/.:])(?:(?:us|eu|ap|apac|au|jp|global)\.)?(?:anthropic\.)?claude-opus-4[.-]7(?:$|[-.:/])",
            model_ref,
            re.IGNORECASE,
        )
    )


def is_opus47_or_newer_bedrock_model_ref(model_ref: str) -> bool:
    return is_opus47_bedrock_model_ref(model_ref) or _is_opus48_bedrock_model_ref(model_ref)


def _is_mythos_preview_bedrock_model_ref(model_ref: str) -> bool:
    return bool(
        re.search(
            r"(?:^|[/.:])(?:(?:us|eu|ap|apac|au|jp|global)\.)?(?:anthropic\.)?claude-mythos-preview(?:$|[-.:/])",
            model_ref,
            re.IGNORECASE,
        )
    )


def is_latest_adaptive_bedrock_model_ref(
    model_id: str,
    params: dict[str, Any] | None = None,
) -> bool:
    model_ref = {"id": model_id}
    if params is not None:
        model_ref["params"] = params
    canonical_model_id = resolve_claude_model_identity(model_ref)
    return (
        resolve_claude_fable5_model_identity(model_ref) is not None
        or any(
            is_opus47_or_newer_bedrock_model_ref(candidate)
            or _is_mythos_preview_bedrock_model_ref(candidate)
            for candidate in [model_id, canonical_model_id]
        )
    )


def supports_bedrock_native_max_effort(
    model_id: str,
    params: dict[str, Any] | None = None,
) -> bool:
    model_ref = {"id": model_id}
    if params is not None:
        model_ref["params"] = params
    if resolve_claude_fable5_model_identity(model_ref):
        return True
    canonical_model_id = resolve_claude_model_identity(model_ref)
    return any(
        _is_opus46_bedrock_model_ref(model_ref_candidate)
        or is_opus47_or_newer_bedrock_model_ref(model_ref_candidate)
        for model_ref_candidate in [model_id, canonical_model_id]
    )


def resolve_bedrock_native_thinking_level_map(
    model_id: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    model_ref = {"id": model_id}
    if params is not None:
        model_ref["params"] = params
    if resolve_claude_fable5_model_identity(model_ref):
        return {"off": "low", "minimal": "low", "xhigh": "xhigh", "max": "max"}
    if not supports_bedrock_native_max_effort(model_id, params):
        return None
    canonical_model_id = resolve_claude_model_identity(model_ref)
    return {
        "xhigh": "xhigh" if any(is_opus47_or_newer_bedrock_model_ref(c) for c in [model_id, canonical_model_id]) else None,
        "max": "max",
    }


def resolve_bedrock_claude_thinking_profile(
    model_id: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trimmed = model_id.strip()
    model_ref = {"id": trimmed}
    if params is not None:
        model_ref["params"] = params
    canonical_model_id = resolve_claude_model_identity(model_ref)
    model_refs = [trimmed, canonical_model_id]

    if resolve_claude_fable5_model_identity(model_ref):
        return {
            "levels": [*_BASE_CLAUDE_THINKING_LEVELS, {"id": "xhigh"}, {"id": "adaptive"}, {"id": "max"}],
            "defaultLevel": "high",
            "preserveWhenCatalogReasoningFalse": True,
        }
    if any(_is_opus48_bedrock_model_ref(r) for r in model_refs):
        return {
            "levels": [*_BASE_CLAUDE_THINKING_LEVELS, {"id": "xhigh"}, {"id": "adaptive"}, {"id": "max"}],
            "defaultLevel": "off",
        }
    if any(is_opus47_bedrock_model_ref(r) for r in model_refs):
        return {
            "levels": [*_BASE_CLAUDE_THINKING_LEVELS, {"id": "xhigh"}, {"id": "adaptive"}, {"id": "max"}],
            "defaultLevel": "off",
        }
    if any(_is_opus46_bedrock_model_ref(r) for r in model_refs):
        return {
            "levels": [*_BASE_CLAUDE_THINKING_LEVELS, {"id": "adaptive"}, {"id": "max"}],
            "defaultLevel": "adaptive",
        }
    if any(_is_mythos_preview_bedrock_model_ref(r) for r in model_refs):
        return {
            "levels": [*_BASE_CLAUDE_THINKING_LEVELS, {"id": "adaptive"}],
            "defaultLevel": "adaptive",
        }
    if any(re.search(r"claude-sonnet-4(?:\.|-)6(?:$|[-.])", r, re.IGNORECASE) for r in model_refs):
        return {
            "levels": [*_BASE_CLAUDE_THINKING_LEVELS, {"id": "adaptive"}],
            "defaultLevel": "adaptive",
        }
    return {"levels": _BASE_CLAUDE_THINKING_LEVELS}


__all__ = [
    "is_latest_adaptive_bedrock_model_ref",
    "is_opus47_bedrock_model_ref",
    "is_opus47_or_newer_bedrock_model_ref",
    "resolve_bedrock_claude_thinking_profile",
    "resolve_bedrock_native_thinking_level_map",
    "supports_bedrock_native_max_effort",
]