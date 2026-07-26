"""Stream wrapper for Cloudflare AI Gateway Anthropic Messages compatibility quirks."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from openclaw.plugin_sdk.provider_stream_shared import (
    create_anthropic_thinking_prefill_payload_wrapper,
)

_log = logging.getLogger("cloudflare-ai-gateway-stream")


def _should_patch_anthropic_messages_payload(model: dict[str, Any] | None) -> bool:
    if not model:
        return True
    api = model.get("api")
    return api is None or api == "anthropic-messages"


def create_cloudflare_ai_gateway_anthropic_thinking_prefill_wrapper(
    base_stream_fn: Callable[..., Any] | None,
) -> Callable[..., Any]:
    def on_stripped(stripped: int) -> None:
        suffix = "" if stripped == 1 else "s"
        _log.warning(
            "removed %s trailing assistant prefill message%s because Anthropic extended "
            "thinking requires conversations to end with a user turn",
            stripped,
            suffix,
        )

    return create_anthropic_thinking_prefill_payload_wrapper(base_stream_fn, on_stripped)


def wrap_cloudflare_ai_gateway_provider_stream(
    ctx: dict[str, Any],
) -> Callable[..., Any] | None:
    model = ctx.get("model")
    if not _should_patch_anthropic_messages_payload(model if isinstance(model, dict) else None):
        return ctx.get("streamFn")
    return create_cloudflare_ai_gateway_anthropic_thinking_prefill_wrapper(ctx.get("streamFn"))


class _TestingExports:
    log = _log
    should_patch_anthropic_messages_payload = staticmethod(_should_patch_anthropic_messages_payload)


testing = _TestingExports()
__testing__ = testing
