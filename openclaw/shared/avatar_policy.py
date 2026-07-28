"""Avatar policy helpers resolve avatar paths and provider fallback rules."""

from __future__ import annotations

import mimetypes
import os
import re
from typing import Any


AVATAR_MAX_BYTES = 2 * 1024 * 1024

_LOCAL_AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}

_AVATAR_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}

_AVATAR_DATA_RE = re.compile(r"^data:", re.IGNORECASE)
_AVATAR_IMAGE_DATA_RE = re.compile(r"^data:image/", re.IGNORECASE)
_AVATAR_HTTP_RE = re.compile(r"^https?://", re.IGNORECASE)
_AVATAR_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
_WINDOWS_ABS_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_AVATAR_PATH_EXT_RE = re.compile(r"\.(png|jpe?g|gif|webp|svg|ico)$", re.IGNORECASE)


def _normalize_lowercase_or_empty(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def resolve_avatar_mime(file_path: str) -> str:
    ext = _normalize_lowercase_or_empty(os.path.splitext(file_path)[1])
    return _AVATAR_MIME_BY_EXT.get(ext, "application/octet-stream")


def is_avatar_data_url(value: str) -> bool:
    return bool(_AVATAR_DATA_RE.match(value))


def is_avatar_image_data_url(value: str) -> bool:
    return bool(_AVATAR_IMAGE_DATA_RE.match(value))


def is_avatar_http_url(value: str) -> bool:
    return bool(_AVATAR_HTTP_RE.match(value))


def has_avatar_uri_scheme(value: str) -> bool:
    return bool(_AVATAR_SCHEME_RE.match(value))


def is_windows_absolute_path(value: str) -> bool:
    return bool(_WINDOWS_ABS_RE.match(value))


def is_workspace_relative_avatar_path(value: str) -> bool:
    if not value:
        return False
    if value.startswith("~"):
        return False
    if has_avatar_uri_scheme(value) and not is_windows_absolute_path(value):
        return False
    return True


def is_path_within_root(root_dir: str, target_path: str) -> bool:
    try:
        target_abs = os.path.abspath(target_path)
        root_abs = os.path.abspath(root_dir)
        return target_abs.startswith(root_abs)
    except (ValueError, OSError):
        return False


def looks_like_avatar_path(value: str) -> bool:
    if "\\" in value or "/" in value:
        return True
    return bool(_AVATAR_PATH_EXT_RE.match(value))


def is_supported_local_avatar_extension(file_path: str) -> bool:
    ext = _normalize_lowercase_or_empty(os.path.splitext(file_path)[1])
    return ext in _LOCAL_AVATAR_EXTENSIONS
