"""Public web-search registration helpers for provider plugins."""

from __future__ import annotations

import math
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
from urllib.parse import urlparse

import httpx

from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty
from openclaw.plugin_sdk.provider_http import read_provider_text_response

T = TypeVar("T")

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_CACHE_TTL_MINUTES = 15
DEFAULT_SEARCH_COUNT = 5
MAX_SEARCH_COUNT = 10
DEFAULT_CACHE_MAX_ENTRIES = 100

CacheEntry = dict[str, Any]


def resolve_timeout_seconds(value: Any, fallback: int) -> int:
    parsed = value if isinstance(value, (int, float)) and math.isfinite(value) else fallback
    return min(86_400, max(1, math.floor(parsed)))


def resolve_cache_ttl_ms(value: Any, fallback_minutes: int) -> int:
    minutes = (
        value if isinstance(value, (int, float)) and math.isfinite(value) else fallback_minutes
    )
    minutes = max(0, minutes)
    return round(minutes * 60_000)


def normalize_cache_key(value: str) -> str:
    return normalize_lowercase_string_or_empty(value)


def read_cache(
    cache: dict[str, CacheEntry],
    key: str,
) -> dict[str, Any] | None:
    entry = cache.get(key)
    if not entry:
        return None
    now_ms = time.time() * 1000
    if now_ms > entry["expires_at"]:
        cache.pop(key, None)
        return None
    return {"value": entry["value"], "cached": True}


def write_cache(
    cache: dict[str, CacheEntry],
    key: str,
    value: Any,
    ttl_ms: int,
) -> None:
    if ttl_ms <= 0:
        return
    now_ms = time.time() * 1000
    if len(cache) >= DEFAULT_CACHE_MAX_ENTRIES:
        oldest_key = next(iter(cache), None)
        if oldest_key is not None:
            cache.pop(oldest_key, None)
    cache[key] = {
        "value": value,
        "expires_at": now_ms + ttl_ms,
        "inserted_at": now_ms,
    }


def resolve_search_count(value: Any, fallback: int) -> int:
    parsed = value if isinstance(value, (int, float)) and math.isfinite(value) else fallback
    return max(1, min(MAX_SEARCH_COUNT, math.floor(parsed)))


def resolve_site_name(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return urlparse(url).hostname
    except ValueError:
        return None


async def read_response_text(
    response: httpx.Response,
    *,
    max_bytes: int | None = None,
) -> dict[str, Any]:
    """Read at most max_bytes from a response body."""
    limit = max_bytes
    if limit is not None and (not isinstance(limit, int) or limit <= 0):
        limit = None

    if limit:
        parts: list[bytes] = []
        bytes_read = 0
        truncated = False
        try:
            async for chunk in response.aiter_bytes():
                if not chunk:
                    continue
                if bytes_read + len(chunk) > limit:
                    remaining = max(0, limit - bytes_read)
                    if remaining <= 0:
                        truncated = True
                        break
                    chunk = chunk[:remaining]
                    truncated = True
                bytes_read += len(chunk)
                parts.append(chunk)
                if truncated or bytes_read >= limit:
                    truncated = True
                    break
        except httpx.HTTPError:
            pass
        finally:
            if truncated:
                await response.aclose()
        return {
            "text": b"".join(parts).decode("utf-8", errors="replace"),
            "truncated": truncated,
            "bytes_read": bytes_read,
        }

    content = await response.aread()
    return {
        "text": content.decode("utf-8", errors="replace"),
        "truncated": False,
        "bytes_read": len(content),
    }


async def with_trusted_web_search_endpoint(
    params: dict[str, Any],
    run: Callable[[httpx.Response], Awaitable[T]],
) -> T:
    """Fetch a trusted web-search endpoint and run a callback on the response."""
    init = params.get("init") or {}
    method = str(init.get("method") or "GET").upper()
    headers = init.get("headers") or {}
    timeout_seconds = resolve_timeout_seconds(
        params.get("timeout_seconds"), DEFAULT_TIMEOUT_SECONDS
    )
    timeout = httpx.Timeout(timeout_seconds)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.request(method, params["url"], headers=headers)
        try:
            return await run(response)
        finally:
            await response.aclose()


__all__ = [
    "DEFAULT_CACHE_TTL_MINUTES",
    "DEFAULT_SEARCH_COUNT",
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_SEARCH_COUNT",
    "normalize_cache_key",
    "read_cache",
    "read_provider_text_response",
    "read_response_text",
    "resolve_cache_ttl_ms",
    "resolve_search_count",
    "resolve_site_name",
    "resolve_timeout_seconds",
    "with_trusted_web_search_endpoint",
    "write_cache",
]
