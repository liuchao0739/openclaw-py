from __future__ import annotations

import mimetypes

IMAGE_MIME_INLINE_SET = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}

TEXT_INLINE_MIME_SET = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "text/html",
    "application/json",
    "application/xml",
    "text/xml",
}

TEXT_INLINE_MAX_BYTES = 8 * 1024


def mime_from_extension(file_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"