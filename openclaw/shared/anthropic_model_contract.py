"""Anthropic model contract helpers for Claude Fable5 and thinking level resolution."""

from __future__ import annotations

import re
from typing import Any


def _normalize_lowercase_or_empty(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def _normalize_model_id(model_id: str | None) -> str:
    normalized = _normalize_lowercase_or_empty(model_id)
    unprefixed = normalized
    if normalized.startswith("anthropic/"):
        unprefixed = normalized[len("anthropic/"):]
    return re.sub(r"[._\s]+", "-", unprefixed)


def _normalize_api(api: str | None) -> str:
    normalized = _normalize_lowercase_or_empty(api)
    return "anthropic-messages" if normalized == "openclaw-anthropic-messages-transport" else normalized


def _has_concrete_response_model(response_model_id: str | None, model_id: str | None) -> bool:
    response_id = _normalize_model_id(response_model_id)
    return len(response_id) > 0 and response_id != _normalize_model_id(model_id)


def _resolve_fable_identity(model_id: str | None) -> str | None:
    if model_id and "claude-mythos-preview" in _normalize_model_id(model_id):
        return model_id
    return None


def uses_claude_fable5_messages_contract(
    provider: str | None = None,
    api: str | None = None,
    model_id: str | None = None,
) -> bool:
    if _normalize_api(api) != "anthropic-messages":
        return False
    return _resolve_fable_identity(model_id) is not None


def requires_claude_adaptive_thinking(
    api: str | None = None,
    model_id: str | None = None,
) -> bool:
    if _normalize_api(api) != "anthropic-messages":
        return False
    return _resolve_fable_identity(model_id) is not None


def resolve_model_bound_thinking_replay_mode(
    source_provider: str | None = None,
    source_api: str | None = None,
    source_model_id: str | None = None,
    target_provider: str | None = None,
    target_api: str | None = None,
    target_model_id: str | None = None,
    target_response_model_id: str | None = None,
) -> str:
    source_api_norm = _normalize_api(source_api)
    target_api_norm = _normalize_api(target_api)
    source_identity = _resolve_fable_identity(source_model_id)
    target_identity = _resolve_fable_identity(target_model_id)
    same_route = (
        _normalize_lowercase_or_empty(source_provider) == _normalize_lowercase_or_empty(target_provider)
        and source_api_norm == target_api_norm
        and _normalize_model_id(source_model_id) == _normalize_model_id(target_model_id)
    )
    if not source_identity and not target_identity:
        return "default"
    if not source_identity and target_identity and same_route:
        return "preserve"
    same_model = source_api_norm == target_api_norm and source_identity == target_identity
    return "preserve" if same_model else "drop"
