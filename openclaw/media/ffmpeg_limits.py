"""Shared ffmpeg/ffprobe buffer and timeout limits.

Mirrors src/media/ffmpeg-limits.ts.
"""

MEDIA_FFMPEG_MAX_BUFFER_BYTES = 10 * 1024 * 1024
MEDIA_FFPROBE_TIMEOUT_MS = 10_000
MEDIA_FFMPEG_TIMEOUT_MS = 45_000
MEDIA_FFMPEG_MAX_AUDIO_DURATION_SECS = 20 * 60
