"""Fireworks plugin stream behavior."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from openclaw.plugin_sdk.provider_stream_shared import create_payload_patch_stream_wrapper
from openclaw_extensions.fireworks.model_id import is_fireworks_kimi_model_id


def _normalize_provider_id(provider_id: str) -> str:
    return provider_id.strip().lower()


def _is_fireworks_provider_id(provider_id: str) -> bool:
    normalized = _normalize_provider_id(provider_id)
    return normalized in {"fireworks", "fireworks-ai"}


def _patch_fireworks_kimi_payload(params: dict[str, Any]) -> None:
    payload = params["payload"]
    # Fireworks Kimi can emit chain-of-thought in visible `content` unless
    # the Anthropic-style thinking toggle is explicitly disabled.
    payload["thinking"] = {"type": "disabled"}
    payload.pop("reasoning", None)
    payload.pop("reasoning_effort", None)
    payload.pop("reasoningEffort", None)


def create_fireworks_kimi_thinking_disabled_wrapper(
    base_stream_fn: Callable[..., Any] | None,
) -> Callable[..., Any]:
    return create_payload_patch_stream_wrapper(base_stream_fn, _patch_fireworks_kimi_payload)


def wrap_fireworks_provider_stream(ctx: dict[str, Any]) -> Callable[..., Any] | None:
    model = ctx.get("model") or {}
    if (
        not _is_fireworks_provider_id(str(ctx.get("provider", "")))
        or model.get("api") != "openai-completions"
        or not is_fireworks_kimi_model_id(str(ctx.get("modelId", "")))
    ):
        return None
    return create_fireworks_kimi_thinking_disabled_wrapper(ctx.get("streamFn"))
