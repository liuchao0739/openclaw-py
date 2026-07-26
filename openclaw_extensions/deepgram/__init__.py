"""Deepgram media understanding extension."""

from openclaw_extensions.deepgram.audio import (
    DEFAULT_DEEPGRAM_AUDIO_BASE_URL,
    DEFAULT_DEEPGRAM_AUDIO_MODEL,
    transcribe_deepgram_audio,
)
from openclaw_extensions.deepgram.media_understanding_provider import (
    deepgram_media_understanding_provider,
)
from openclaw_extensions.deepgram.realtime_transcription_provider import (
    build_deepgram_realtime_transcription_provider,
    testing,
)

__all__ = [
    "DEFAULT_DEEPGRAM_AUDIO_BASE_URL",
    "DEFAULT_DEEPGRAM_AUDIO_MODEL",
    "build_deepgram_realtime_transcription_provider",
    "deepgram_media_understanding_provider",
    "testing",
    "transcribe_deepgram_audio",
]
