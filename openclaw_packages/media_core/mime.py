from __future__ import annotations

import mimetypes
import os
import re
from urllib.parse import urlparse

from .constants import MediaKind, media_kind_from_mime
from .lazy_import import LazyPromiseLoader, create_lazy_import_loader

FILE_TYPE_SNIFF_MAX_BYTES = 1024 * 1024

EXT_BY_MIME: dict[str, str] = {
    "image/heic": ".heic",
    "image/heif": ".heif",
    "image/bmp": ".bmp",
    "image/jpg": ".jpg",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/wave": ".wav",
    "audio/x-wav": ".wav",
    "audio/flac": ".flac",
    "audio/aac": ".aac",
    "audio/opus": ".opus",
    "audio/webm": ".webm",
    "audio/x-m4a": ".m4a",
    "audio/mp4": ".m4a",
    "audio/x-caf": ".caf",
    "video/x-msvideo": ".avi",
    "video/mp4": ".mp4",
    "video/x-matroska": ".mkv",
    "video/webm": ".webm",
    "video/x-flv": ".flv",
    "video/x-ms-wmv": ".wmv",
    "video/quicktime": ".mov",
    "application/pdf": ".pdf",
    "application/json": ".json",
    "application/yaml": ".yaml",
    "application/zip": ".zip",
    "application/gzip": ".gz",
    "application/x-tar": ".tar",
    "application/x-7z-compressed": ".7z",
    "application/vnd.rar": ".rar",
    "application/msword": ".doc",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/csv": ".csv",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/html": ".html",
    "text/xml": ".xml",
    "text/css": ".css",
    "application/xml": ".xml",
}


def _build_mime_by_ext() -> dict[str, str]:
    by_ext: dict[str, str] = {}
    for mime, ext in EXT_BY_MIME.items():
        if ext not in by_ext:
            by_ext[ext] = mime
    return by_ext


MIME_BY_EXT: dict[str, str] = {
    **_build_mime_by_ext(),
    ".jpg": "image/jpeg",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".webm": "video/webm",
    ".jpeg": "image/jpeg",
    ".js": "text/javascript",
    ".log": "text/plain",
    ".htm": "text/html",
    ".xml": "text/xml",
    ".yml": "application/yaml",
}

AUDIO_FILE_EXTENSIONS = frozenset([
    ".aac",
    ".caf",
    ".flac",
    ".m4a",
    ".mp3",
    ".oga",
    ".ogg",
    ".opus",
    ".wav",
])


async def _load_file_type_module():
    import filetype as _filetype
    return _filetype


_file_type_module_loader: LazyPromiseLoader[object] = create_lazy_import_loader(_load_file_type_module)


def normalize_mime_type(mime: str | None) -> str | None:
    if not mime:
        return None
    cleaned = mime.split(";", 1)[0].strip().lower()
    if cleaned == "image/apng":
        return "image/png"
    return cleaned or None


def slice_mime_sniff_buffer(buffer: bytes) -> bytes:
    if len(buffer) <= FILE_TYPE_SNIFF_MAX_BYTES:
        return buffer
    return buffer[:FILE_TYPE_SNIFF_MAX_BYTES]


async def _sniff_mime(buffer: bytes | None) -> str | None:
    if not buffer:
        return None
    try:
        filetype = await _file_type_module_loader.load()
        guess_fn = getattr(filetype, "guess", None)
        if guess_fn is not None:
            result = guess_fn(slice_mime_sniff_buffer(buffer))
            if result is not None:
                if isinstance(result, tuple):
                    mime = result[0] if result else None
                else:
                    mime = str(result)
                if mime:
                    normalized = normalize_mime_type(mime)
                    if normalized:
                        return normalized
    except Exception:
        pass
    return _sniff_known_audio_magic(buffer)


def _sniff_known_audio_magic(buffer: bytes) -> str | None:
    if len(buffer) >= 4 and buffer[:4] == b"caff":
        return "audio/x-caf"
    return None


def get_file_extension(file_path: str | None) -> str | None:
    if not file_path:
        return None
    try:
        if re.match(r"^https?://", file_path, re.IGNORECASE):
            parsed = urlparse(file_path)
            ext = os.path.splitext(parsed.path)[1].lower()
            return ext or None
    except Exception:
        pass
    ext = os.path.splitext(file_path)[1].lower()
    return ext or None


def mime_type_from_file_path(file_path: str | None) -> str | None:
    ext = get_file_extension(file_path)
    if not ext:
        return None
    return MIME_BY_EXT.get(ext)


def is_audio_file_name(file_name: str | None) -> bool:
    ext = get_file_extension(file_name)
    if not ext:
        return False
    return ext in AUDIO_FILE_EXTENSIONS


async def detect_mime(
    buffer: bytes | None = None,
    header_mime: str | None = None,
    file_path: str | None = None,
) -> str | None:
    ext = get_file_extension(file_path)
    ext_mime = MIME_BY_EXT.get(ext) if ext else None

    normalized_header = normalize_mime_type(header_mime)
    sniffed = await _sniff_mime(buffer)
    sniffed_generic_container = sniffed and _is_generic_mime(sniffed)
    trusted_ext_mime = None if (sniffed_generic_container and _is_image_mime(ext_mime)) else ext_mime
    trusted_header_mime = None if (sniffed_generic_container and _is_image_mime(normalized_header)) else normalized_header

    if sniffed and (not _is_generic_mime(sniffed) or not trusted_ext_mime):
        return sniffed
    if trusted_ext_mime:
        return trusted_ext_mime
    if trusted_header_mime and not _is_generic_mime(trusted_header_mime):
        return trusted_header_mime
    if sniffed:
        return sniffed
    if trusted_header_mime:
        return trusted_header_mime
    return None


def _is_generic_mime(mime: str | None) -> bool:
    if not mime:
        return True
    m = mime.lower()
    return m == "application/octet-stream" or m == "application/zip"


def _is_image_mime(mime: str | None) -> bool:
    return media_kind_from_mime(normalize_mime_type(mime)) == "image"


def extension_for_mime(mime: str | None) -> str | None:
    normalized = normalize_mime_type(mime)
    if not normalized:
        return None
    return EXT_BY_MIME.get(normalized)


def is_gif_media(content_type: str | None = None, file_name: str | None = None) -> bool:
    if normalize_mime_type(content_type) == "image/gif":
        return True
    ext = get_file_extension(file_name)
    return ext == ".gif"


def image_mime_from_format(format: str | None) -> str | None:
    if not format:
        return None
    lower = format.lower()
    if lower in ("jpg", "jpeg"):
        return "image/jpeg"
    if lower == "heic":
        return "image/heic"
    if lower == "heif":
        return "image/heif"
    if lower == "png":
        return "image/png"
    if lower == "webp":
        return "image/webp"
    if lower == "gif":
        return "image/gif"
    return None


def kind_from_mime(mime: str | None) -> MediaKind | None:
    return media_kind_from_mime(normalize_mime_type(mime))
