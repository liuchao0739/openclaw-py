"""Redirect header helpers retain only cross-origin-safe request headers.

Mirrors src/infra/net/redirect-headers.ts.
"""

from __future__ import annotations

from typing import Any, Mapping

CROSS_ORIGIN_REDIRECT_SAFE_HEADERS = frozenset(
    {
        "accept",
        "accept-encoding",
        "accept-language",
        "cache-control",
        "content-language",
        "content-type",
        "if-match",
        "if-modified-since",
        "if-none-match",
        "if-unmodified-since",
        "pragma",
        "range",
        "user-agent",
    }
)


def retain_safe_headers_for_cross_origin_redirect(
    headers: Any,
) -> dict[str, str] | None:
    """Keep only headers that are safe to replay after a redirect crosses origins.

    Authorization/cookie-like metadata must be dropped before the follow-up fetch.
    """
    if headers is None:
        return None
    if isinstance(headers, Mapping):
        items = headers.items()
    elif hasattr(headers, "items"):
        items = headers.items()
    else:
        return None
    safe: dict[str, str] = {}
    for key, value in items:
        if isinstance(key, str) and key.strip().lower() in CROSS_ORIGIN_REDIRECT_SAFE_HEADERS:
            safe[key] = str(value)
    return safe
