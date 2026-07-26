"""Cohere OpenAI-compatible completions stream wrapper."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw.plugin_sdk.provider_stream_shared import create_payload_patch_stream_wrapper


def _patch_cohere_payload(payload: dict[str, Any]) -> None:
    # Cohere's Compatibility API uses developer, not system, for instructions.
    messages = payload.get("messages")
    if isinstance(messages, list):
        payload["messages"] = [
            {**message, "role": "developer"}
            if is_record(message) and message.get("role") == "system"
            else message
            for message in messages
        ]

    # Cohere lets tool-capable models choose a tool when tool_choice is omitted.
    payload.pop("tool_choice", None)


def create_cohere_completions_wrapper(
    base_stream_fn: Callable[..., Any] | None,
) -> Callable[..., Any]:
    return create_payload_patch_stream_wrapper(
        base_stream_fn,
        lambda params: _patch_cohere_payload(params["payload"]),
    )
