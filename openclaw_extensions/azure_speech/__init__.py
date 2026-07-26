"""Azure Speech text-to-speech extension."""

from openclaw_extensions.azure_speech.speech_provider import build_azure_speech_provider
from openclaw_extensions.azure_speech.tts import (
    DEFAULT_AZURE_SPEECH_AUDIO_FORMAT,
    DEFAULT_AZURE_SPEECH_LANG,
    DEFAULT_AZURE_SPEECH_TELEPHONY_FORMAT,
    DEFAULT_AZURE_SPEECH_VOICE,
    DEFAULT_AZURE_SPEECH_VOICE_NOTE_FORMAT,
    azure_speech_t_t_s,
    azure_speech_tts,
    build_azure_speech_ssml,
    infer_azure_speech_file_extension,
    is_azure_speech_voice_compatible,
    list_azure_speech_voices,
    normalize_azure_speech_base_url,
)

__all__ = [
    "DEFAULT_AZURE_SPEECH_AUDIO_FORMAT",
    "DEFAULT_AZURE_SPEECH_LANG",
    "DEFAULT_AZURE_SPEECH_TELEPHONY_FORMAT",
    "DEFAULT_AZURE_SPEECH_VOICE",
    "DEFAULT_AZURE_SPEECH_VOICE_NOTE_FORMAT",
    "azure_speech_t_t_s",
    "azure_speech_tts",
    "build_azure_speech_provider",
    "build_azure_speech_ssml",
    "infer_azure_speech_file_extension",
    "is_azure_speech_voice_compatible",
    "list_azure_speech_voices",
    "normalize_azure_speech_base_url",
]
