"""Base64 mime sniffing helpers infer media types from encoded payload bytes.

Mirrors src/media/sniff-mime-from-base64.ts. Self-contained port with
magic-byte detection for common formats.
"""

from __future__ import annotations

import base64
import re


def _canonicalize_base64(value: str) -> str | None:
    """Canonicalize base64 by removing whitespace and padding inconsistencies."""
    if not value:
        return None
    cleaned = re.sub(r"\s+", "", value)
    if not cleaned:
        return None
    return cleaned


def _detect_mime(buffer: bytes) -> str | None:
    """Detect MIME type from magic bytes."""
    if len(buffer) < 4:
        return None
    # PNG
    if buffer[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    # JPEG
    if buffer[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    # GIF
    if buffer[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    # WebP (RIFF....WEBP)
    if buffer[:4] == b"RIFF" and len(buffer) >= 12 and buffer[8:12] == b"WEBP":
        return "image/webp"
    # BMP
    if buffer[:2] == b"BM":
        return "image/bmp"
    # PDF
    if buffer[:5] == b"%PDF-":
        return "application/pdf"
    # MP3
    if buffer[:3] == b"ID3" or (buffer[:2] == b"\xff\xfb"):
        return "audio/mpeg"
    # WAV (RIFF....WAVE)
    if buffer[:4] == b"RIFF" and len(buffer) >= 12 and buffer[8:12] == b"WAVE":
        return "audio/wav"
    # OGG
    if buffer[:4] == b"OggS":
        return "audio/ogg"
    # MP4 (ftyp)
    if len(buffer) >= 12 and buffer[4:8] == b"ftyp":
        return "video/mp4"
    # WebM
    if buffer[:4] == b"\x1a\x45\xdf\xa3":
        return "video/webm"
    return None


async def sniff_mime_from_base64(base64_str: str) -> str | None:
    """Sniff a MIME type from canonical base64 without decoding the full payload."""
    if not isinstance(base64_str, str):
        return None
    trimmed = base64_str.strip()
    canonical = _canonicalize_base64(trimmed) if trimmed else None
    if not canonical:
        return None
    take = min(256, len(canonical))
    slice_len = take - (take % 4)
    if slice_len < 8:
        return None
    try:
        head = base64.b64decode(canonical[:slice_len])
        return _detect_mime(head)
    except Exception:
        return None
