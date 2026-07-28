"""Runtime import helpers for lazy modules."""

from __future__ import annotations

from typing import Any


def resolve_runtime_import_specifier(base_url: str, parts: list[str]) -> str:
    joined = "".join(parts)
    from .import_specifier import to_safe_import_path
    safe_joined = to_safe_import_path(joined)
    if safe_joined != joined:
        return safe_joined
    from urllib.parse import urljoin
    return urljoin(to_safe_import_path(base_url), joined)
