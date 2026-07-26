"""Gradium speech provider extension."""

from openclaw_extensions.gradium.shared import (
    DEFAULT_GRADIUM_VOICE_ID,
    GRADIUM_VOICES,
    normalize_gradium_base_url,
)
from openclaw_extensions.gradium.speech_provider import build_gradium_speech_provider
from openclaw_extensions.gradium.tts import gradium_tts

__all__ = [
    "DEFAULT_GRADIUM_VOICE_ID",
    "GRADIUM_VOICES",
    "build_gradium_speech_provider",
    "gradium_tts",
    "normalize_gradium_base_url",
]
