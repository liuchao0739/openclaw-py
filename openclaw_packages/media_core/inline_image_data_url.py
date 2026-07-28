from __future__ import annotations

import base64 as _base64
from dataclasses import dataclass

from .base64 import canonicalize_base64

INLINE_IMAGE_DATA_URL_PREFIX = "data:"


@dataclass(frozen=True)
class _ImageSignature:
    mime: str
    offset: int
    length: int
    pattern: bytes


_IMAGE_SIGNATURES: list[_ImageSignature] = [
    _ImageSignature(
        mime="image/png",
        offset=0,
        length=8,
        pattern=bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]),
    ),
    _ImageSignature(
        mime="image/jpeg",
        offset=0,
        length=3,
        pattern=bytes([0xFF, 0xD8, 0xFF]),
    ),
    _ImageSignature(
        mime="image/gif",
        offset=0,
        length=6,
        pattern=b"GIF87a",
    ),
    _ImageSignature(
        mime="image/gif",
        offset=0,
        length=6,
        pattern=b"GIF89a",
    ),
    _ImageSignature(
        mime="image/bmp",
        offset=0,
        length=2,
        pattern=bytes([0x42, 0x4D]),
    ),
]

HEIC_BRANDS = frozenset(["heic", "heix", "hevc", "hevx", "heis", "heim", "hevm", "hevs"])
HEIF_BRANDS = frozenset(["mif1", "msf1"])
IMAGE_SIGNATURE_PREFIX_BASE64_CHARS = 128
INLINE_IMAGE_DATA_URL_MIMES = frozenset(["image/png", "image/jpeg", "image/webp", "image/gif"])


def _starts_with_data_url(value: str) -> bool:
    return value[: len(INLINE_IMAGE_DATA_URL_PREFIX)].lower() == INLINE_IMAGE_DATA_URL_PREFIX


def _sniff_iso_bmff_image_mime(buffer: bytes) -> str | None:
    if len(buffer) < 12 or buffer[4:8].decode("ascii", errors="replace") != "ftyp":
        return None
    brands = [buffer[8:12].decode("ascii", errors="replace")]
    offset = 16
    while offset + 4 <= len(buffer):
        brands.append(buffer[offset : offset + 4].decode("ascii", errors="replace"))
        offset += 4
    if any(brand in HEIC_BRANDS for brand in brands):
        return "image/heic"
    if any(brand in HEIF_BRANDS for brand in brands):
        return "image/heif"
    return None


def _is_webp(buffer: bytes) -> bool:
    return (
        len(buffer) >= 12
        and buffer[:4] == b"RIFF"
        and buffer[8:12] == b"WEBP"
    )


def sniff_inline_image_mime(buffer: bytes) -> str | None:
    if _is_webp(buffer):
        return "image/webp"
    for signature in _IMAGE_SIGNATURES:
        start = signature.offset
        end = start + signature.length
        if len(buffer) < end:
            continue
        if buffer[start:end] == signature.pattern:
            return signature.mime
    return _sniff_iso_bmff_image_mime(buffer)


def _is_image_mime_type(value: str) -> bool:
    return value.strip().lower().startswith("image/")


@dataclass(frozen=True)
class SanitizedInlineImageBase64:
    mime_type: str
    base64: str


def sanitize_inline_image_base64(mime_type: str, base64: str) -> SanitizedInlineImageBase64 | None:
    if not _is_image_mime_type(mime_type):
        return None
    canonical_payload = canonicalize_base64(base64)
    if not canonical_payload:
        return None
    prefix_b64 = canonical_payload[:IMAGE_SIGNATURE_PREFIX_BASE64_CHARS]
    try:
        prefix_bytes = _base64.b64decode(prefix_b64, validate=False)
    except Exception:
        return None
    sniffed = sniff_inline_image_mime(prefix_bytes)
    if not sniffed:
        return None
    return SanitizedInlineImageBase64(mime_type=sniffed, base64=canonical_payload)


def _parse_inline_image_data_url(value: str) -> tuple[list[str], str] | None:
    if not _starts_with_data_url(value):
        return ([], value)
    comma_index = value.find(",")
    if comma_index < 0:
        return None
    metadata_part = value[len(INLINE_IMAGE_DATA_URL_PREFIX) : comma_index]
    metadata = [part.strip() for part in metadata_part.split(";")]
    payload = value[comma_index + 1 :]
    return (metadata, payload)


def _metadata_allows_image_base64(metadata: list[str]) -> bool:
    if not metadata:
        return False
    mime = metadata[0]
    if not mime or not _is_image_mime_type(mime):
        return False
    options = metadata[1:]
    return any(part.lower() == "base64" for part in options)


def _sanitize_inline_image_data_url_with_allowed_mimes(image_url: str, allowed_mimes: set[str] | None = None) -> str | None:
    parsed = _parse_inline_image_data_url(image_url)
    if parsed is None:
        return None
    metadata, payload = parsed
    if not metadata:
        return image_url
    if not _metadata_allows_image_base64(metadata):
        return None
    mime_type = metadata[0] if metadata else ""
    sanitized = sanitize_inline_image_base64(mime_type, payload)
    if not sanitized:
        return None
    if allowed_mimes and sanitized.mime_type not in allowed_mimes:
        return None
    return f"data:{sanitized.mime_type};base64,{sanitized.base64}"


def sanitize_inline_image_data_url_for_storage(image_url: str) -> str | None:
    return _sanitize_inline_image_data_url_with_allowed_mimes(image_url)


def sanitize_inline_image_data_url(image_url: str) -> str | None:
    return _sanitize_inline_image_data_url_with_allowed_mimes(image_url, set(INLINE_IMAGE_DATA_URL_MIMES))
