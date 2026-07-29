from typing import Optional

from .thinking_policy import resolve_fireworks_thinking_profile, ThinkingProfile


def resolve_thinking_profile(params: dict) -> Optional[ThinkingProfile]:
    return resolve_fireworks_thinking_profile(params["modelId"])
