"""Public web-search registration helpers for provider plugins."""

from __future__ import annotations

import calendar
import contextlib
import math
import os
import re
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
from urllib.parse import urlparse

import httpx

from openclaw.packages.normalization_core import is_record, normalize_lowercase_string_or_empty
from openclaw.plugin_sdk.provider_http import read_provider_text_response
from openclaw.utils.normalize_secret_input import normalize_optional_secret_input

T = TypeVar("T")

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_CACHE_TTL_MINUTES = 15
DEFAULT_SEARCH_COUNT = 5
MAX_SEARCH_COUNT = 10
DEFAULT_CACHE_MAX_ENTRIES = 100

CacheEntry = dict[str, Any]
SearchConfigRecord = dict[str, Any]

SEARCH_CACHE: dict[str, CacheEntry] = {}

_ISO_DATE_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_PERPLEXITY_DATE_PATTERN = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


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


def resolve_search_timeout_seconds(search_config: SearchConfigRecord | None = None) -> int:
    return resolve_timeout_seconds(
        search_config.get("timeoutSeconds") if search_config else None,
        DEFAULT_TIMEOUT_SECONDS,
    )


def resolve_search_cache_ttl_ms(search_config: SearchConfigRecord | None = None) -> int:
    return resolve_cache_ttl_ms(
        search_config.get("cacheTtlMinutes") if search_config else None,
        DEFAULT_CACHE_TTL_MINUTES,
    )


def read_configured_secret_string(value: Any, _path: str) -> str | None:
    return normalize_optional_secret_input(value)


def read_provider_env_value(env_vars: list[str]) -> str | None:
    for env_var in env_vars:
        value = normalize_optional_secret_input(os.environ.get(env_var))
        if value:
            return value
    return None


def resolve_provider_web_search_plugin_config(
    config: dict[str, Any] | None,
    plugin_id: str,
) -> dict[str, Any] | None:
    if not config or not is_record(config.get("plugins")):
        return None
    entries = config["plugins"].get("entries")
    if not is_record(entries):
        return None
    plugin_entry = entries.get(plugin_id)
    if not is_record(plugin_entry):
        return None
    plugin_config = plugin_entry.get("config")
    if not is_record(plugin_config):
        return None
    web_search = plugin_config.get("webSearch")
    return dict(web_search) if is_record(web_search) else None


def merge_scoped_search_config(
    search_config: dict[str, Any] | None,
    key: str,
    plugin_config: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not plugin_config:
        return search_config
    current_scoped: dict[str, Any] = {}
    if search_config and is_record(search_config.get(key)):
        current_scoped = dict(search_config[key])
    next_config = dict(search_config) if search_config else {}
    next_config[key] = {**current_scoped, **plugin_config}
    return next_config


def build_search_cache_key(parts: list[Any]) -> str:
    return normalize_cache_key(":".join("default" if part is None else str(part) for part in parts))


def read_cached_search_payload(cache_key: str) -> dict[str, Any] | None:
    cached = read_cache(SEARCH_CACHE, cache_key)
    if not cached:
        return None
    payload = dict(cached["value"])
    payload["cached"] = True
    return payload


def write_cached_search_payload(
    cache_key: str,
    payload: dict[str, Any],
    ttl_ms: int,
) -> None:
    write_cache(SEARCH_CACHE, cache_key, payload, ttl_ms)


def _is_valid_iso_date(value: str) -> bool:
    if not _ISO_DATE_PATTERN.fullmatch(value):
        return False
    year, month, day = (int(part) for part in value.split("-"))
    if month < 1 or month > 12 or day < 1:
        return False
    last_day = calendar.monthrange(year, month)[1]
    return day <= last_day


def normalize_to_iso_date(value: str) -> str | None:
    trimmed = value.strip()
    if _ISO_DATE_PATTERN.fullmatch(trimmed):
        return trimmed if _is_valid_iso_date(trimmed) else None
    match = _PERPLEXITY_DATE_PATTERN.fullmatch(trimmed)
    if match:
        month, day, year = match.groups()
        iso = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return iso if _is_valid_iso_date(iso) else None
    return None


def parse_iso_date_range(
    *,
    raw_date_after: str | None = None,
    raw_date_before: str | None = None,
    invalid_date_after_message: str,
    invalid_date_before_message: str,
    invalid_date_range_message: str,
    docs: str = "https://docs.openclaw.ai/tools/web",
) -> dict[str, Any]:
    date_after = normalize_to_iso_date(raw_date_after) if raw_date_after else None
    if raw_date_after and not date_after:
        return {
            "error": "invalid_date",
            "message": invalid_date_after_message,
            "docs": docs,
        }

    date_before = normalize_to_iso_date(raw_date_before) if raw_date_before else None
    if raw_date_before and not date_before:
        return {
            "error": "invalid_date",
            "message": invalid_date_before_message,
            "docs": docs,
        }

    if date_after and date_before and date_after > date_before:
        return {
            "error": "invalid_date_range",
            "message": invalid_date_range_message,
            "docs": docs,
        }

    return {"dateAfter": date_after, "dateBefore": date_before}


async def read_response_text_limited(response: Any, limit_bytes: int = 16 * 1024) -> str:
    if limit_bytes <= 0:
        return ""
    result = await read_response_text(response, max_bytes=limit_bytes)
    return result["text"]


def resolve_site_name(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return urlparse(url).hostname
    except ValueError:
        return None


async def read_response_text(
    response: Any,
    *,
    max_bytes: int | None = None,
) -> dict[str, Any]:
    """Read at most max_bytes from a response body."""
    limit = max_bytes
    if limit is not None and (not isinstance(limit, int) or limit <= 0):
        limit = None

    if limit:
        body = getattr(response, "body", None)
        reader = body.get_reader() if body is not None and hasattr(body, "get_reader") else None
        if reader is not None:
            parts: list[bytes] = []
            bytes_read = 0
            truncated = False
            try:
                while True:
                    chunk, done = await reader.read()
                    if done:
                        break
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
            finally:
                if truncated:
                    with contextlib.suppress(Exception):
                        await reader.cancel()
            return {
                "text": b"".join(parts).decode("utf-8", errors="replace"),
                "truncated": truncated,
                "bytes_read": bytes_read,
            }

        parts = []
        bytes_read = 0
        truncated = False
        try:
            if hasattr(response, "aiter_bytes"):
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
            if truncated and hasattr(response, "aclose"):
                await response.aclose()
        return {
            "text": b"".join(parts).decode("utf-8", errors="replace"),
            "truncated": truncated,
            "bytes_read": bytes_read,
        }

    if hasattr(response, "aread"):
        content = await response.aread()
    elif hasattr(response, "text"):
        content = (await response.text()).encode("utf-8")
    else:
        content = b""
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
    body = init.get("body")
    content = body.encode("utf-8") if isinstance(body, str) else body
    timeout_seconds = resolve_timeout_seconds(
        params.get("timeout_seconds"), DEFAULT_TIMEOUT_SECONDS
    )
    timeout = httpx.Timeout(timeout_seconds)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.request(
            method,
            params["url"],
            headers=headers,
            content=content,
        )
        try:
            return await run(response)
        finally:
            await response.aclose()


__all__ = [
    "DEFAULT_CACHE_TTL_MINUTES",
    "DEFAULT_SEARCH_COUNT",
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_SEARCH_COUNT",
    "SEARCH_CACHE",
    "SearchConfigRecord",
    "build_search_cache_key",
    "merge_scoped_search_config",
    "normalize_cache_key",
    "normalize_to_iso_date",
    "parse_iso_date_range",
    "read_cache",
    "read_cached_search_payload",
    "read_configured_secret_string",
    "read_provider_env_value",
    "read_provider_text_response",
    "read_response_text",
    "read_response_text_limited",
    "resolve_cache_ttl_ms",
    "resolve_provider_web_search_plugin_config",
    "resolve_search_cache_ttl_ms",
    "resolve_search_count",
    "resolve_search_timeout_seconds",
    "resolve_site_name",
    "resolve_timeout_seconds",
    "with_trusted_web_search_endpoint",
    "write_cache",
    "write_cached_search_payload",
]
