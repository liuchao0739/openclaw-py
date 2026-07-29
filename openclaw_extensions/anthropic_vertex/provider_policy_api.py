from typing import Optional

from openclaw.plugin_sdk.provider_model_shared import resolve_claude_thinking_profile


def resolve_thinking_profile(params: dict) -> Optional[dict]:
    if params["provider"].strip().lower() != "anthropic-vertex":
        return None
    return resolve_claude_thinking_profile(
        params["modelId"],
        params.get("params"),
        {"includeNativeMax": True},
    )
