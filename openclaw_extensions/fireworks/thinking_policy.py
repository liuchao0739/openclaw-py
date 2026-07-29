from typing import TypedDict, Optional, List

from .model_id import is_fireworks_kimi_model_id


class ThinkingLevel(TypedDict):
    id: str


class ThinkingProfile(TypedDict):
    levels: List[ThinkingLevel]
    defaultLevel: str


FIREWORKS_KIMI_THINKING_PROFILE: ThinkingProfile = {
    "levels": [{"id": "off"}],
    "defaultLevel": "off",
}


def resolve_fireworks_thinking_profile(model_id: str) -> Optional[ThinkingProfile]:
    if not is_fireworks_kimi_model_id(model_id):
        return None
    return FIREWORKS_KIMI_THINKING_PROFILE
