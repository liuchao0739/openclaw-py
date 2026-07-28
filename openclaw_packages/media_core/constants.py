from __future__ import annotations

MAX_IMAGE_BYTES = 6 * 1024 * 1024
MAX_AUDIO_BYTES = 16 * 1024 * 1024
MAX_VIDEO_BYTES = 16 * 1024 * 1024
MAX_DOCUMENT_BYTES = 100 * 1024 * 1024

MEDIA_KIND_IMAGE = "image"
MEDIA_KIND_AUDIO = "audio"
MEDIA_KIND_VIDEO = "video"
MEDIA_KIND_DOCUMENT = "document"

MediaKind = str


def media_kind_from_mime(mime: str | None) -> str | None:
    if not mime:
        return None
    if mime.startswith("image/"):
        return MEDIA_KIND_IMAGE
    if mime.startswith("audio/"):
        return MEDIA_KIND_AUDIO
    if mime.startswith("video/"):
        return MEDIA_KIND_VIDEO
    if mime == "application/pdf":
        return MEDIA_KIND_DOCUMENT
    if mime.startswith("text/"):
        return MEDIA_KIND_DOCUMENT
    if mime.startswith("application/"):
        return MEDIA_KIND_DOCUMENT
    return None


def max_bytes_for_kind(kind: str) -> int:
    if kind == MEDIA_KIND_IMAGE:
        return MAX_IMAGE_BYTES
    if kind == MEDIA_KIND_AUDIO:
        return MAX_AUDIO_BYTES
    if kind == MEDIA_KIND_VIDEO:
        return MAX_VIDEO_BYTES
    if kind == MEDIA_KIND_DOCUMENT:
        return MAX_DOCUMENT_BYTES
    return MAX_DOCUMENT_BYTES
