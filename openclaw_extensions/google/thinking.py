from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class ThinkingConfig:
    enabled: bool = False
    include_thinking: bool = True
    reasoning_effort: Optional[str] = None
    type: str = "google_thinking"

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "type": self.type,
            "enabled": self.enabled,
            "includeThinking": self.include_thinking,
        }
        if self.reasoning_effort:
            result["reasoningEffort"] = self.reasoning_effort
        return result


@dataclass
class ThinkingProfile:
    name: str
    reasoning_effort: str = "MEDIUM"
    include_thinking: bool = True
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "reasoning_effort": self.reasoning_effort,
            "include_thinking": self.include_thinking,
            "enabled": self.enabled,
        }


THINKING_PROFILES: Dict[str, ThinkingProfile] = {
    "default": ThinkingProfile(
        name="default",
        reasoning_effort="MEDIUM",
        include_thinking=True,
        enabled=True,
    ),
    "light": ThinkingProfile(
        name="light",
        reasoning_effort="LOW",
        include_thinking=True,
        enabled=True,
    ),
    "balanced": ThinkingProfile(
        name="balanced",
        reasoning_effort="MEDIUM",
        include_thinking=True,
        enabled=True,
    ),
    "deep": ThinkingProfile(
        name="deep",
        reasoning_effort="HIGH",
        include_thinking=True,
        enabled=True,
    ),
}

VALID_REASONING_EFFORTS = ["LOW", "MEDIUM", "HIGH"]


def resolve_thinking_config(
    thinking_enabled: Optional[bool] = None,
    reasoning_effort: Optional[str] = None,
    thinking_profile: Optional[str] = None,
) -> ThinkingConfig:
    config = ThinkingConfig()

    if thinking_profile and thinking_profile in THINKING_PROFILES:
        profile = THINKING_PROFILES[thinking_profile]
        config.enabled = profile.enabled
        config.reasoning_effort = profile.reasoning_effort
        config.include_thinking = profile.include_thinking
        return config

    if thinking_enabled is not None:
        config.enabled = thinking_enabled
    else:
        config.enabled = bool(reasoning_effort)

    if reasoning_effort:
        effort_upper = reasoning_effort.upper()
        if effort_upper in VALID_REASONING_EFFORTS:
            config.reasoning_effort = effort_upper

    return config


def get_available_profiles() -> List[Dict[str, Any]]:
    return [profile.to_dict() for profile in THINKING_PROFILES.values()]