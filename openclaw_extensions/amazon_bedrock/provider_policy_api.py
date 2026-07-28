from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.provider_model_shared import normalize_provider_id
from openclaw_extensions.amazon_bedrock.thinking_policy import (
    resolve_bedrock_claude_thinking_profile,
)


def resolve_thinking_profile(params: dict[str, Any]) -> dict[str, Any] | None:
    if normalize_provider_id(params.get("provider", "")) != "amazon-bedrock":
        return None
    return resolve_bedrock_claude_thinking_profile(
        params.get("modelId", ""),
        params.get("params"),
    )


__all__ = ["resolve_thinking_profile"]