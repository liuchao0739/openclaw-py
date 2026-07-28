from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class GoogleThinkingProfile:
    name: str
    description: str = ""
    reasoning_effort: Optional[str] = None
    include_thinking: bool = True


@dataclass
class GoogleThinkingReasoningEffort:
    low: str = "LOW"
    medium: str = "MEDIUM"
    high: str = "HIGH"


@dataclass
class GoogleThinkingConfig:
    enabled: bool = False
    reasoning_effort: Optional[str] = None
    include_thinking: bool = True
    profile: Optional[GoogleThinkingProfile] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "enabled": self.enabled,
            "include_thinking": self.include_thinking,
        }
        if self.reasoning_effort:
            result["reasoning_effort"] = self.reasoning_effort
        if self.profile:
            result["profile"] = self.profile.__dict__
        return result


GOOGLE_THINKING_PROFILES: Dict[str, GoogleThinkingProfile] = {
    "default": GoogleThinkingProfile(
        name="default",
        description="Default thinking profile with medium reasoning effort",
        reasoning_effort="MEDIUM",
        include_thinking=True,
    ),
    "light": GoogleThinkingProfile(
        name="light",
        description="Light thinking profile with low reasoning effort for faster responses",
        reasoning_effort="LOW",
        include_thinking=True,
    ),
    "balanced": GoogleThinkingProfile(
        name="balanced",
        description="Balanced thinking profile with medium reasoning effort",
        reasoning_effort="MEDIUM",
        include_thinking=True,
    ),
    "deep": GoogleThinkingProfile(
        name="deep",
        description="Deep thinking profile with high reasoning effort for complex tasks",
        reasoning_effort="HIGH",
        include_thinking=True,
    ),
}

VALID_REASONING_EFFORTS = ["LOW", "MEDIUM", "HIGH"]


def resolve_google_thinking_config(
    thinking_enabled: Optional[bool] = None,
    reasoning_effort: Optional[str] = None,
    thinking_profile: Optional[str] = None,
) -> GoogleThinkingConfig:
    config = GoogleThinkingConfig()

    if thinking_enabled is not None:
        config.enabled = thinking_enabled
    elif thinking_profile and thinking_profile in GOOGLE_THINKING_PROFILES:
        profile = GOOGLE_THINKING_PROFILES[thinking_profile]
        config.profile = profile
        config.enabled = True
        config.reasoning_effort = profile.reasoning_effort
        config.include_thinking = profile.include_thinking
        return config
    elif reasoning_effort:
        config.enabled = True
        config.reasoning_effort = reasoning_effort.upper() if reasoning_effort else None
        config.include_thinking = True
        return config

    if not config.enabled:
        config.enabled = False
        config.include_thinking = False

    return config


def apply_google_thinking_config(
    request_body: Dict[str, Any],
    thinking_config: GoogleThinkingConfig,
) -> Dict[str, Any]:
    if not thinking_config.enabled:
        return request_body

    generation_config = request_body.get("generationConfig", {})

    if thinking_config.reasoning_effort:
        generation_config["reasoningEffort"] = thinking_config.reasoning_effort

    if not thinking_config.include_thinking:
        generation_config["includeThinking"] = False
    else:
        generation_config["includeThinking"] = True

    request_body["generationConfig"] = generation_config
    return request_body