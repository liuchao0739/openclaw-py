"""Groq provider module implements model/runtime integration."""

from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.media_understanding import transcribe_open_ai_compatible_audio

DEFAULT_GROQ_AUDIO_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_AUDIO_MODEL = "whisper-large-v3-turbo"


async def _transcribe_groq_audio(req: dict[str, Any]) -> dict[str, str]:
    return await transcribe_open_ai_compatible_audio(
        {
            **req,
            "baseUrl": req.get("baseUrl") or DEFAULT_GROQ_AUDIO_BASE_URL,
            "defaultBaseUrl": DEFAULT_GROQ_AUDIO_BASE_URL,
            "defaultModel": DEFAULT_GROQ_AUDIO_MODEL,
        }
    )


groq_media_understanding_provider: dict[str, Any] = {
    "id": "groq",
    "capabilities": ["audio"],
    "defaultModels": {"audio": DEFAULT_GROQ_AUDIO_MODEL},
    "autoPriority": {"audio": 20},
    "transcribeAudio": _transcribe_groq_audio,
}
