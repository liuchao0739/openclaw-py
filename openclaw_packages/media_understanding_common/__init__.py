"""Public barrel for media-understanding shared contracts and helpers."""

from __future__ import annotations

from .active_model import ActiveMediaModel
from .defaults import (
    CLI_OUTPUT_MAX_BUFFER,
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_CHARS,
    DEFAULT_MAX_CHARS_BY_CAPABILITY,
    DEFAULT_MEDIA_CONCURRENCY,
    DEFAULT_PROMPT,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_VIDEO_MAX_BASE64_BYTES,
    MIN_AUDIO_FILE_BYTES,
)
from .errors import MediaUnderstandingSkipError, is_media_understanding_skip_error
from .format import (
    extract_media_user_text,
    format_audio_transcripts,
    format_media_understanding_body,
)
from .openai_compatible_video import (
    OpenAiCompatibleVideoPayload,
    build_open_ai_compatible_video_request_body,
    coerce_open_ai_compatible_video_text,
    resolve_media_understanding_string,
)
from .output_extract import extract_gemini_response
from .provider_id import (
    normalize_media_execution_provider_id,
    normalize_media_provider_id,
)
from .provider_supports import provider_supports_capability
from .types import (
    MediaAttachment,
    MediaUnderstandingCapability,
    MediaUnderstandingCapabilityRegistry,
    MediaUnderstandingKind,
    MediaUnderstandingOutput,
    MediaUnderstandingProvider,
)
from .video import estimate_base64_size, resolve_video_max_base64_bytes

__all__ = [
    "CLI_OUTPUT_MAX_BUFFER",
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_CHARS",
    "DEFAULT_MAX_CHARS_BY_CAPABILITY",
    "DEFAULT_MEDIA_CONCURRENCY",
    "DEFAULT_PROMPT",
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_VIDEO_MAX_BASE64_BYTES",
    "MIN_AUDIO_FILE_BYTES",
    "ActiveMediaModel",
    "MediaAttachment",
    "MediaUnderstandingCapability",
    "MediaUnderstandingCapabilityRegistry",
    "MediaUnderstandingKind",
    "MediaUnderstandingOutput",
    "MediaUnderstandingProvider",
    "MediaUnderstandingSkipError",
    "OpenAiCompatibleVideoPayload",
    "build_open_ai_compatible_video_request_body",
    "coerce_open_ai_compatible_video_text",
    "estimate_base64_size",
    "extract_gemini_response",
    "extract_media_user_text",
    "format_audio_transcripts",
    "format_media_understanding_body",
    "is_media_understanding_skip_error",
    "normalize_media_execution_provider_id",
    "normalize_media_provider_id",
    "provider_supports_capability",
    "resolve_media_understanding_string",
    "resolve_video_max_base64_bytes",
]
