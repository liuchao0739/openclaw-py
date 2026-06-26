"""Media package — ffmpeg limits, temp files, mime sniffing."""

from .ffmpeg_limits import (
    MEDIA_FFMPEG_MAX_BUFFER_BYTES,
    MEDIA_FFPROBE_TIMEOUT_MS,
    MEDIA_FFMPEG_TIMEOUT_MS,
    MEDIA_FFMPEG_MAX_AUDIO_DURATION_SECS,
)
from .temp_files import unlink_if_exists
from .sniff_mime_from_base64 import sniff_mime_from_base64

__all__ = [
    "MEDIA_FFMPEG_MAX_BUFFER_BYTES",
    "MEDIA_FFPROBE_TIMEOUT_MS",
    "MEDIA_FFMPEG_TIMEOUT_MS",
    "MEDIA_FFMPEG_MAX_AUDIO_DURATION_SECS",
    "unlink_if_exists",
    "sniff_mime_from_base64",
]
