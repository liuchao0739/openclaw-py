from typing import Optional, Dict, Any, List

from .thinking import (
    ThinkingConfig,
    ThinkingProfile,
    THINKING_PROFILES,
    resolve_thinking_config,
    get_available_profiles,
    VALID_REASONING_EFFORTS,
)


def resolve_google_thinking_config(
    thinking_enabled: Optional[bool] = None,
    reasoning_effort: Optional[str] = None,
    thinking_profile: Optional[str] = None,
) -> ThinkingConfig:
    return resolve_thinking_config(
        thinking_enabled=thinking_enabled,
        reasoning_effort=reasoning_effort,
        thinking_profile=thinking_profile,
    )


def list_google_thinking_profiles() -> List[Dict[str, Any]]:
    return get_available_profiles()


def get_google_thinking_profile(name: str) -> Optional[ThinkingProfile]:
    return THINKING_PROFILES.get(name)


def validate_google_reasoning_effort(effort: str) -> bool:
    return effort.upper() in VALID_REASONING_EFFORTS


def apply_google_thinking_to_request(
    request_body: Dict[str, Any],
    thinking_config: ThinkingConfig,
) -> Dict[str, Any]:
    if not thinking_config.enabled:
        return request_body

    generation_config = request_body.get("generationConfig", {})

    if thinking_config.reasoning_effort:
        generation_config["reasoningEffort"] = thinking_config.reasoning_effort

    generation_config["includeThinking"] = thinking_config.include_thinking

    request_body["generationConfig"] = generation_config
    return request_body