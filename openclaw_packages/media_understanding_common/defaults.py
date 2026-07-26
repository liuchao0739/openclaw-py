"""Shared defaults for media-understanding limits, prompts, and concurrency."""

from __future__ import annotations

from .types import MediaUnderstandingCapability

_MB = 1024 * 1024

# Default max response characters for bounded text outputs.
DEFAULT_MAX_CHARS = 500
# Default max response characters by capability.
DEFAULT_MAX_CHARS_BY_CAPABILITY: dict[MediaUnderstandingCapability, int | None] = {
    "image": DEFAULT_MAX_CHARS,
    "audio": None,
    "video": DEFAULT_MAX_CHARS,
}
# Default input byte limits by capability.
DEFAULT_MAX_BYTES: dict[MediaUnderstandingCapability, int] = {
    "image": 10 * _MB,
    "audio": 20 * _MB,
    "video": 50 * _MB,
}
# Default request timeout by capability.
DEFAULT_TIMEOUT_SECONDS: dict[MediaUnderstandingCapability, int] = {
    "image": 60,
    "audio": 60,
    "video": 120,
}
# Default prompts by capability.
DEFAULT_PROMPT: dict[MediaUnderstandingCapability, str] = {
    "image": "Describe the image.",
    "audio": "Transcribe the audio.",
    "video": "Describe the video.",
}
# Upper bound for base64-expanded video payloads.
DEFAULT_VIDEO_MAX_BASE64_BYTES = 70 * _MB
# CLI output buffer used by provider child processes.
CLI_OUTPUT_MAX_BUFFER = 5 * _MB
# Default parallel media-understanding request count.
DEFAULT_MEDIA_CONCURRENCY = 2
# Minimum bytes for audio files before transcription is attempted.
MIN_AUDIO_FILE_BYTES = 1024
