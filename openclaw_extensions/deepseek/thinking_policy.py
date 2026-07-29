from typing import TypedDict, Optional, List

from .models import is_deepseek_v4_model_id


class ThinkingLevel(TypedDict):
    id: str


class ThinkingProfile(TypedDict):
    levels: List[ThinkingLevel]
    defaultLevel: str


V4_THINKING_LEVEL_IDS = ["off", "minimal", "low", "medium", "high", "xhigh", "max"]


def _build_deepseek_v4_thinking_level(level_id: str) -> ThinkingLevel:
    return {"id": level_id}


DEEPSEEK_V4_THINKING_PROFILE: ThinkingProfile = {
    "levels": [_build_deepseek_v4_thinking_level(level_id) for level_id in V4_THINKING_LEVEL_IDS],
    "defaultLevel": "high",
}


def resolve_deepseek_v4_thinking_profile(model_id: str) -> Optional[ThinkingProfile]:
    if is_deepseek_v4_model_id(model_id):
        return DEEPSEEK_V4_THINKING_PROFILE
    return None
