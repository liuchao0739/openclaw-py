"""Deepgram provider module implements model/runtime integration."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.deepgram.audio import transcribe_deepgram_audio

deepgram_media_understanding_provider: dict[str, Any] = {
    "id": "deepgram",
    "capabilities": ["audio"],
    "defaultModels": {"audio": "nova-3"},
    "autoPriority": {"audio": 30},
    "transcribeAudio": transcribe_deepgram_audio,
}
