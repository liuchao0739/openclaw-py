from __future__ import annotations

from typing import Any

from .cli_shared import CLAUDE_CLI_OFF_THINKING_PROFILE
from .config_defaults import (
    apply_anthropic_config_defaults,
    normalize_anthropic_provider_config_for_provider,
)


def normalize_config(params: dict[str, Any]) -> Any:
    return normalize_anthropic_provider_config_for_provider(params)


def apply_config_defaults(params: dict[str, Any]) -> Any:
    return apply_anthropic_config_defaults(params)


def resolve_thinking_profile(params: dict[str, Any]) -> dict[str, Any] | None:
    provider = params.get("provider", "").strip().lower()
    model_id = params.get("modelId", "")

    try:
        from openclaw.plugin_sdk.provider_model_shared import (
            resolve_claude_model_identity,
            resolve_claude_thinking_profile,
        )
        contract_model_id = resolve_claude_model_identity({
            "id": model_id,
            "params": params.get("params"),
        })
    except ImportError:
        contract_model_id = model_id

    if provider == "anthropic":
        try:
            from openclaw.plugin_sdk.provider_model_shared import (
                resolve_claude_thinking_profile,
            )
            return resolve_claude_thinking_profile(
                contract_model_id, None, includeNativeMax=True
            )
        except ImportError:
            return None
    if provider == "claude-cli":
        if contract_model_id.startswith("claude-fable-5"):
            return CLAUDE_CLI_OFF_THINKING_PROFILE
        try:
            from openclaw.plugin_sdk.provider_model_shared import (
                resolve_claude_thinking_profile,
            )
            return resolve_claude_thinking_profile(
                contract_model_id, None, includeNativeMax=True
            )
        except ImportError:
            return None
    return None