"""Converts a Headers object to a plain record for provider request handling.

Mirrors src/llm/utils/headers.ts.
"""

from __future__ import annotations

from typing import Any, Mapping


def headers_to_record(headers: Any) -> dict[str, str]:
    """Convert a Headers-like object to a plain dict."""
    result: dict[str, str] = {}
    if headers is None:
        return result
    # Try .items() first (dict-like)
    if hasattr(headers, "items"):
        for key, value in headers.items():
            result[str(key)] = str(value)
        return result
    # Try .entries() (Headers-like)
    if hasattr(headers, "entries"):
        for key, value in headers.entries():
            result[str(key)] = str(value)
        return result
    if isinstance(headers, Mapping):
        for key, value in headers.items():
            result[str(key)] = str(value)
    return result
