"""Strip username/password credentials from URL strings.

Mirrors packages/net-policy/src/url-userinfo.ts.
"""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

__all__ = ["strip_url_user_info"]


def strip_url_user_info(value: str) -> str:
    try:
        parsed = urlparse(value)
        if not parsed.scheme and not parsed.netloc:
            return value
        if not parsed.username and not parsed.password:
            return value
        hostname = parsed.hostname or ""
        if parsed.port is not None:
            host = f"{hostname}:{parsed.port}"
        else:
            host = hostname
        netloc = host
        rebuilt = parsed._replace(netloc=netloc)
        return urlunparse(rebuilt)
    except ValueError:
        return value
