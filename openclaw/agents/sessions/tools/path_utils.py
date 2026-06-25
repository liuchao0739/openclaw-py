"""Session tool path normalization helpers.

Expands user/file URL inputs and resolves read/write paths against the active
cwd with macOS filename variants.
"""

from __future__ import annotations

import os
import re
import unicodedata
from urllib.parse import urlparse, unquote

_UNICODE_SPACES = re.compile(r"[\u00A0\u2000-\u200A\u202F\u205F\u3000]")
_NARROW_NO_BREAK_SPACE = "\u202F"


def _normalize_unicode_spaces(s: str) -> str:
    return _UNICODE_SPACES.sub(" ", s)


def _try_macos_screenshot_path(file_path: str) -> str:
    return re.sub(r" (AM|PM)\.", f"{_NARROW_NO_BREAK_SPACE}\\1.", file_path, flags=re.IGNORECASE)


def _try_nfd_variant(file_path: str) -> str:
    return unicodedata.normalize("NFD", file_path)


def _try_curly_quote_variant(file_path: str) -> str:
    return file_path.replace("'", "\u2019")


def _file_exists(file_path: str) -> bool:
    return os.path.exists(file_path)


def _normalize_at_prefix(file_path: str) -> str:
    return file_path[1:] if file_path.startswith("@") else file_path


def _expand_path(file_path: str) -> str:
    normalized = _normalize_unicode_spaces(_normalize_at_prefix(file_path))
    if normalized.startswith("file://"):
        try:
            parsed = urlparse(normalized)
            if parsed.path:
                return unquote(parsed.path)
        except Exception:
            pass
        return normalized
    if normalized == "~":
        return os.path.expanduser("~")
    if normalized.startswith("~/"):
        return os.path.expanduser("~") + normalized[1:]
    return normalized


def resolve_to_cwd(file_path: str, cwd: str) -> str:
    """Resolve a path relative to the given cwd, handling ~ and absolute paths."""
    expanded = _expand_path(file_path)
    if os.path.isabs(expanded):
        return expanded
    return os.path.abspath(os.path.join(cwd, expanded))


def resolve_read_path(file_path: str, cwd: str) -> str:
    """Resolve a read path, trying macOS filename variants if the file doesn't exist."""
    resolved = resolve_to_cwd(file_path, cwd)

    if _file_exists(resolved):
        return resolved

    # Try macOS AM/PM variant
    am_pm_variant = _try_macos_screenshot_path(resolved)
    if am_pm_variant != resolved and _file_exists(am_pm_variant):
        return am_pm_variant

    # Try NFD variant
    nfd_variant = _try_nfd_variant(resolved)
    if nfd_variant != resolved and _file_exists(nfd_variant):
        return nfd_variant

    # Try curly quote variant
    curly_variant = _try_curly_quote_variant(resolved)
    if curly_variant != resolved and _file_exists(curly_variant):
        return curly_variant

    # Try combined NFD + curly quote
    nfd_curly_variant = _try_curly_quote_variant(nfd_variant)
    if nfd_curly_variant != resolved and _file_exists(nfd_curly_variant):
        return nfd_curly_variant

    return resolved
