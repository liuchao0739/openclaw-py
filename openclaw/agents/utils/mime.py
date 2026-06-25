"""Lightweight MIME sniffing helpers for agent image inputs.

Detects supported image MIME types from leading file bytes without trusting
file extensions.
"""

from __future__ import annotations

_IMAGE_TYPE_SNIFF_BYTES = 4100
_PNG_SIGNATURE = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])


def _starts_with(buffer: bytes, signature: bytes) -> bool:
    if len(buffer) < len(signature):
        return False
    return buffer[:len(signature)] == signature


def _starts_with_ascii(buffer: bytes, offset: int, text: str) -> bool:
    if len(buffer) < offset + len(text):
        return False
    return buffer[offset:offset + len(text)] == text.encode("ascii")


def _read_uint32_be(buffer: bytes, offset: int) -> int:
    if offset + 4 > len(buffer):
        return 0
    return int.from_bytes(buffer[offset:offset + 4], byteorder="big")


def _is_png(buffer: bytes) -> bool:
    return (
        len(buffer) >= 16
        and _read_uint32_be(buffer, len(_PNG_SIGNATURE)) == 13
        and _starts_with_ascii(buffer, 12, "IHDR")
    )


def _is_animated_png(buffer: bytes) -> bool:
    offset = len(_PNG_SIGNATURE)
    while offset + 8 <= len(buffer):
        chunk_length = _read_uint32_be(buffer, offset)
        chunk_type_offset = offset + 4
        if _starts_with_ascii(buffer, chunk_type_offset, "acTL"):
            return True
        if _starts_with_ascii(buffer, chunk_type_offset, "IDAT"):
            return False
        next_offset = offset + 8 + chunk_length + 4
        if next_offset <= offset or next_offset > len(buffer):
            return False
        offset = next_offset
    return False


def detect_supported_image_mime_type(buffer: bytes) -> str | None:
    """Detect supported image MIME type from leading file bytes."""
    if _starts_with(buffer, bytes([0xFF, 0xD8, 0xFF])):
        return None if len(buffer) > 3 and buffer[3] == 0xF7 else "image/jpeg"
    if _starts_with(buffer, _PNG_SIGNATURE):
        return "image/png" if _is_png(buffer) and not _is_animated_png(buffer) else None
    if _starts_with_ascii(buffer, 0, "GIF"):
        return "image/gif"
    if _starts_with_ascii(buffer, 0, "RIFF") and _starts_with_ascii(buffer, 8, "WEBP"):
        return "image/webp"
    return None


async def detect_supported_image_mime_type_from_file(file_path: str) -> str | None:
    """Read a bounded prefix from disk and detect its supported image MIME type."""
    try:
        with open(file_path, "rb") as f:
            buffer = f.read(_IMAGE_TYPE_SNIFF_BYTES)
        return detect_supported_image_mime_type(buffer)
    except Exception:
        return None
