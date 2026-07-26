"""Brave Search HTTP runtime."""

from __future__ import annotations

import ipaddress
import json
import logging
import re
import socket
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse, urlunparse

from openclaw.agents.tools.common import read_positive_integer_param, read_string_param
from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty
from openclaw.plugin_sdk.provider_http import read_response_with_limit
from openclaw.plugin_sdk.provider_web_search import (
    DEFAULT_SEARCH_COUNT,
    MAX_SEARCH_COUNT,
    SearchConfigRecord,
    build_search_cache_key,
    normalize_to_iso_date,
    parse_iso_date_range,
    read_cached_search_payload,
    read_configured_secret_string,
    read_provider_env_value,
    read_response_text_limited,
    resolve_search_cache_ttl_ms,
    resolve_search_count,
    resolve_search_timeout_seconds,
    resolve_site_name,
    with_trusted_web_search_endpoint,
    write_cached_search_payload,
)
from openclaw.security.external_content import wrap_web_content
from openclaw_extensions.brave.src.brave_web_search_provider_shared import (
    map_brave_llm_context_results,
    normalize_brave_country,
    normalize_brave_language_params,
    resolve_brave_config,
    resolve_brave_mode,
)

DEFAULT_BRAVE_BASE_URL = "https://api.search.brave.com"
BRAVE_SEARCH_ENDPOINT_PATH = "/res/v1/web/search"
BRAVE_LLM_CONTEXT_ENDPOINT_PATH = "/res/v1/llm/context"
PROVIDER_JSON_RESPONSE_MAX_BYTES = 16 * 1024 * 1024
ERROR_BODY_LIMIT_BYTES = 16 * 1024
ERROR_DETAIL_LIMIT = 220

BRAVE_FRESHNESS_SHORTCUTS = {"pd", "pw", "pm", "py"}
BRAVE_FRESHNESS_RANGE = re.compile(r"^(\d{4}-\d{2}-\d{2})to(\d{4}-\d{2}-\d{2})$")
PERPLEXITY_RECENCY_VALUES = {"day", "week", "month", "year"}
RECENCY_TO_FRESHNESS = {
    "day": "pd",
    "week": "pw",
    "month": "pm",
    "year": "py",
}

brave_http_logger = logging.getLogger("brave/http")
brave_http_log_records: list[tuple[str, dict[str, Any] | None]] = []


def _emit_brave_http_log(event: str, meta: dict[str, Any] | None = None) -> None:
    brave_http_logger.info("brave http %s", event)
    brave_http_log_records.append((event, meta))


def _log_brave_http(
    diagnostics: dict[str, Any] | None,
    event: str,
    meta: dict[str, Any] | None = None,
) -> None:
    if not diagnostics or not diagnostics.get("enabled"):
        return
    _emit_brave_http_log(event, meta)


def _truncate_error_detail(detail: str, limit: int = ERROR_DETAIL_LIMIT) -> str:
    if len(detail) <= limit:
        return detail
    return f"{detail[: limit - 1]}…"


async def _assert_ok_or_throw_provider_error(response: Any, label: str) -> None:
    ok = getattr(response, "is_success", None)
    if ok is None:
        ok = getattr(response, "ok", True)
    if ok:
        return
    status = getattr(response, "status_code", getattr(response, "status", "unknown"))
    detail = await read_response_text_limited(response, ERROR_BODY_LIMIT_BYTES)
    reason = getattr(response, "reason_phrase", None) or ""
    message_detail = _truncate_error_detail(detail or reason or "")
    raise RuntimeError(f"{label} ({status}): {message_detail}" if message_detail else f"{label} ({status})")


async def _read_provider_json_response(response: Any, label: str) -> Any:
    def on_overflow(params: dict[str, int]) -> Exception:
        return RuntimeError(f"{label}: JSON response exceeds {params['maxBytes']} bytes")

    raw = await read_response_with_limit(
        response,
        PROVIDER_JSON_RESPONSE_MAX_BYTES,
        on_overflow=on_overflow,
    )
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as cause:
        raise RuntimeError(f"{label}: malformed JSON response") from cause


def _describe_brave_request_url(url: Any) -> dict[str, Any]:
    from urllib.parse import parse_qsl, urlparse

    parsed = urlparse(str(url))
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    return {
        "url": str(url),
        "query": params.get("q", ""),
        "params": params,
    }


def _resolve_brave_api_key(search_config: SearchConfigRecord | None = None) -> str | None:
    return read_configured_secret_string(
        search_config.get("apiKey") if search_config else None,
        "tools.web.search.apiKey",
    ) or read_provider_env_value(["BRAVE_API_KEY"])


def _resolve_brave_base_url(brave_config: dict[str, Any] | None = None) -> str:
    configured = read_configured_secret_string(
        brave_config.get("baseUrl") if brave_config else None,
        "plugins.entries.brave.config.webSearch.baseUrl",
    )
    if configured:
        return configured.rstrip("/")
    return DEFAULT_BRAVE_BASE_URL


def _build_brave_endpoint_url(base_url: str, endpoint_path: str) -> str:
    parsed = urlparse(base_url)
    base_path = parsed.path.rstrip("/")
    rebuilt = parsed._replace(path=f"{base_path}{endpoint_path}", query="", fragment="")
    return urlunparse(rebuilt)


def _is_private_or_loopback_host(hostname: str) -> bool:
    lowered = hostname.lower()
    if lowered in {"localhost", "127.0.0.1", "::1"} or lowered.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(lowered)
        return address.is_private or address.is_loopback
    except ValueError:
        try:
            infos = socket.getaddrinfo(hostname, None)
        except OSError:
            return False
        if not infos:
            return False
        return all(
            ipaddress.ip_address(info[4][0]).is_private or ipaddress.ip_address(info[4][0]).is_loopback
            for info in infos
            if info[4]
        )


async def _validate_brave_base_url(base_url: str) -> str:
    try:
        parsed = urlparse(base_url)
    except ValueError as cause:
        raise ValueError("Brave Search base URL must be a valid http:// or https:// URL.") from cause
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Brave Search base URL must use http:// or https://.")
    hostname = parsed.hostname or ""
    if parsed.scheme == "http":
        if not _is_private_or_loopback_host(hostname):
            raise ValueError(
                "Brave Search HTTP base URL must target a trusted private or loopback host. "
                "Use https:// for public hosts."
            )
        return "self_hosted"
    return "self_hosted" if _is_private_or_loopback_host(hostname) else "strict"


def _missing_brave_key_payload() -> dict[str, str]:
    return {
        "error": "missing_brave_api_key",
        "message": (
            "web_search (brave) needs a Brave Search API key. Run "
            "`openclaw configure --section web` to store it, or set BRAVE_API_KEY in the "
            "Gateway environment. If you do not want to configure a search API key, use "
            "web_fetch for a specific URL or the browser tool for interactive pages."
        ),
        "docs": "https://docs.openclaw.ai/tools/web",
    }


def _set_brave_search_url_params(
    url: str,
    *,
    query: str,
    country: str | None = None,
    search_lang: str | None = None,
    freshness: str | None = None,
    date_after: str | None = None,
    date_before: str | None = None,
    allow_date_before_only: bool = False,
) -> str:
    from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["q"] = query
    if country:
        params["country"] = country
    if search_lang:
        params["search_lang"] = search_lang
    if freshness:
        params["freshness"] = freshness
    elif date_after and date_before:
        params["freshness"] = f"{date_after}to{date_before}"
    elif date_after:
        today = datetime.now(UTC).date().isoformat()
        params["freshness"] = f"{date_after}to{today}"
    elif allow_date_before_only and date_before:
        params["freshness"] = f"1970-01-01to{date_before}"
    return urlunparse(parsed._replace(query=urlencode(params)))


def _normalize_brave_freshness(value: str | None) -> str | None:
    if not value:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    lower = normalize_lowercase_string_or_empty(trimmed)
    if lower in BRAVE_FRESHNESS_SHORTCUTS:
        return lower
    if lower in PERPLEXITY_RECENCY_VALUES:
        return RECENCY_TO_FRESHNESS[lower]
    match = BRAVE_FRESHNESS_RANGE.match(trimmed)
    if match:
        start, end = match.groups()
        if normalize_to_iso_date(start) and normalize_to_iso_date(end) and start <= end:
            return f"{start}to{end}"
    return None


def _parse_web_search_time_filters(
    *,
    raw_freshness: str | None = None,
    raw_date_after: str | None = None,
    raw_date_before: str | None = None,
    invalid_freshness_message: str,
    invalid_date_after_message: str,
    invalid_date_before_message: str,
    invalid_date_range_message: str,
    docs: str = "https://docs.openclaw.ai/tools/web",
) -> dict[str, Any]:
    freshness = _normalize_brave_freshness(raw_freshness) if raw_freshness else None
    if raw_freshness and not freshness:
        return {
            "error": "invalid_freshness",
            "message": invalid_freshness_message,
            "docs": docs,
        }
    if raw_freshness and (raw_date_after or raw_date_before):
        return {
            "error": "conflicting_time_filters",
            "message": (
                "freshness and date_after/date_before cannot be used together. Use either "
                "freshness (day/week/month/year) or a date range (date_after/date_before), "
                "not both."
            ),
            "docs": docs,
        }
    parsed_date_range = parse_iso_date_range(
        raw_date_after=raw_date_after,
        raw_date_before=raw_date_before,
        invalid_date_after_message=invalid_date_after_message,
        invalid_date_before_message=invalid_date_before_message,
        invalid_date_range_message=invalid_date_range_message,
        docs=docs,
    )
    if "error" in parsed_date_range:
        return parsed_date_range
    if freshness:
        return {
            "freshness": freshness,
            "dateAfter": parsed_date_range.get("dateAfter"),
            "dateBefore": parsed_date_range.get("dateBefore"),
        }
    return parsed_date_range


async def _run_brave_json_request(
    params: dict[str, Any],
    error_label: str,
) -> Any:
    url = _build_brave_endpoint_url(params["base_url"], params["endpoint_path"])
    url = params["configure_url"](url)
    _log_brave_http(
        params.get("diagnostics"),
        "request",
        {"mode": params["mode"], **_describe_brave_request_url(url)},
    )
    started_at = datetime.now(UTC)

    async def handle_response(response: Any) -> Any:
        _log_brave_http(
            params.get("diagnostics"),
            "response",
            {
                "mode": params["mode"],
                "status": getattr(response, "status_code", getattr(response, "status", None)),
                "ok": getattr(response, "is_success", getattr(response, "ok", None)),
                "durationMs": int((datetime.now(UTC) - started_at).total_seconds() * 1000),
            },
        )
        await _assert_ok_or_throw_provider_error(response, error_label)
        return await _read_provider_json_response(response, error_label)

    return await with_trusted_web_search_endpoint(
        {
            "url": url,
            "timeout_seconds": params["timeout_seconds"],
            "init": {
                "method": "GET",
                "headers": {
                    "Accept": "application/json",
                    "X-Subscription-Token": params["api_key"],
                },
            },
        },
        handle_response,
    )


async def _run_brave_llm_context_search(params: dict[str, Any]) -> dict[str, Any]:
    data = await _run_brave_json_request(
        {
            **params,
            "endpoint_path": BRAVE_LLM_CONTEXT_ENDPOINT_PATH,
            "mode": "llm-context",
            "configure_url": lambda url: _set_brave_search_url_params(
                url,
                query=params["query"],
                country=params.get("country"),
                search_lang=params.get("search_lang"),
                freshness=params.get("freshness"),
                date_after=params.get("dateAfter"),
                date_before=params.get("dateBefore"),
            ),
        },
        "Brave LLM Context API error",
    )
    return {
        "results": map_brave_llm_context_results(data),
        "sources": data.get("sources") if isinstance(data, dict) else None,
    }


async def _run_brave_web_search(params: dict[str, Any]) -> list[dict[str, Any]]:
    def configure_url(url: str) -> str:
        url = _set_brave_search_url_params(
            url,
            query=params["query"],
            country=params.get("country"),
            search_lang=params.get("search_lang"),
            freshness=params.get("freshness"),
            date_after=params.get("dateAfter"),
            date_before=params.get("dateBefore"),
            allow_date_before_only=True,
        )
        return _append_count_and_ui_lang(url, params)

    data = await _run_brave_json_request(
        {
            **params,
            "endpoint_path": BRAVE_SEARCH_ENDPOINT_PATH,
            "mode": "web",
            "configure_url": configure_url,
        },
        "Brave Search API error",
    )
    web = data.get("web") if isinstance(data, dict) else None
    results = web.get("results") if isinstance(web, dict) and isinstance(web.get("results"), list) else []
    mapped: list[dict[str, Any]] = []
    for entry in results:
        if not isinstance(entry, dict):
            continue
        description = entry.get("description") or ""
        title = entry.get("title") or ""
        url = entry.get("url") or ""
        mapped.append(
            {
                "title": wrap_web_content(title, "web_search") if title else "",
                "url": url,
                "description": wrap_web_content(description, "web_search") if description else "",
                **({"published": entry["age"]} if entry.get("age") else {}),
                **({"siteName": site_name} if (site_name := resolve_site_name(url)) else {}),
            }
        )
    return mapped


def _append_count_and_ui_lang(url: str, params: dict[str, Any]) -> str:
    from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

    parsed = urlparse(url)
    query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query_params["count"] = str(params["count"])
    if params.get("ui_lang"):
        query_params["ui_lang"] = params["ui_lang"]
    return urlunparse(parsed._replace(query=urlencode(query_params)))


async def execute_brave_search(
    args: dict[str, Any],
    search_config: SearchConfigRecord | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    api_key = _resolve_brave_api_key(search_config)
    if not api_key:
        return _missing_brave_key_payload()

    brave_config = resolve_brave_config(search_config)
    brave_mode = resolve_brave_mode(brave_config)
    brave_base_url = _resolve_brave_base_url(brave_config)
    brave_endpoint_mode = await _validate_brave_base_url(brave_base_url)
    _ = brave_endpoint_mode

    query = read_string_param(args, "query", required=True)
    count = read_positive_integer_param(
        args,
        "count",
        max_value=MAX_SEARCH_COUNT,
        message=f"count must be an integer from 1 to {MAX_SEARCH_COUNT}.",
    )
    if count is None and search_config:
        max_results = search_config.get("maxResults")
        count = max_results if isinstance(max_results, int) else None

    country = normalize_brave_country(read_string_param(args, "country"))
    language = read_string_param(args, "language")
    search_lang = read_string_param(args, "search_lang")
    ui_lang = read_string_param(args, "ui_lang")
    normalized_language = normalize_brave_language_params(
        {
            "search_lang": search_lang or language,
            "ui_lang": ui_lang,
        }
    )

    if normalized_language.get("invalidField") == "search_lang":
        return {
            "error": "invalid_search_lang",
            "message": (
                "search_lang must be a Brave-supported language code like 'en', 'en-gb', "
                "'zh-hans', or 'zh-hant'."
            ),
            "docs": "https://docs.openclaw.ai/tools/web",
        }
    if normalized_language.get("invalidField") == "ui_lang":
        return {
            "error": "invalid_ui_lang",
            "message": "ui_lang must be a language-region locale like 'en-US'.",
            "docs": "https://docs.openclaw.ai/tools/web",
        }
    if normalized_language.get("ui_lang") and brave_mode == "llm-context":
        return {
            "error": "unsupported_ui_lang",
            "message": (
                "ui_lang is not supported by Brave llm-context mode. Remove ui_lang or use "
                "Brave web mode for locale-based UI hints."
            ),
            "docs": "https://docs.openclaw.ai/tools/web",
        }

    parsed_time_filters = _parse_web_search_time_filters(
        raw_freshness=read_string_param(args, "freshness"),
        raw_date_after=read_string_param(args, "date_after"),
        raw_date_before=read_string_param(args, "date_before"),
        invalid_freshness_message="freshness must be day, week, month, or year.",
        invalid_date_after_message="date_after must be YYYY-MM-DD format.",
        invalid_date_before_message="date_before must be YYYY-MM-DD format.",
        invalid_date_range_message="date_after must be before date_before.",
    )
    if "error" in parsed_time_filters:
        return parsed_time_filters

    freshness = parsed_time_filters.get("freshness")
    date_after = parsed_time_filters.get("dateAfter")
    date_before = parsed_time_filters.get("dateBefore")

    if brave_mode == "llm-context":
        today = datetime.now(UTC).date().isoformat()
        if date_after and not date_before and date_after > today:
            return {
                "error": "invalid_date_range",
                "message": "date_after cannot be in the future for Brave llm-context mode.",
                "docs": "https://docs.openclaw.ai/tools/web",
            }
        if date_before and not date_after:
            return {
                "error": "unsupported_date_filter",
                "message": (
                    "Brave llm-context mode requires date_after when date_before is set. "
                    "Use a bounded date range or freshness."
                ),
                "docs": "https://docs.openclaw.ai/tools/web",
            }

    llm_context_date_end = (
        date_before or datetime.now(UTC).date().isoformat()
        if brave_mode == "llm-context" and date_after
        else date_before
    )
    cache_key = build_search_cache_key(
        [
            "brave",
            brave_mode,
            brave_base_url,
            query,
            *(
                [
                    country,
                    normalized_language.get("search_lang"),
                    freshness,
                    date_after,
                    llm_context_date_end,
                ]
                if brave_mode == "llm-context"
                else [
                    resolve_search_count(count, DEFAULT_SEARCH_COUNT),
                    country,
                    normalized_language.get("search_lang"),
                    normalized_language.get("ui_lang"),
                    freshness,
                    date_after,
                    date_before,
                ]
            ),
        ]
    )
    diagnostics = {"enabled": options.get("diagnostics_enabled") is True} if options else None
    cached = read_cached_search_payload(cache_key)
    if cached:
        _log_brave_http(diagnostics, "cache hit", {"mode": brave_mode, "query": query, "cacheKey": cache_key})
        return cached
    _log_brave_http(diagnostics, "cache miss", {"mode": brave_mode, "query": query, "cacheKey": cache_key})

    start = datetime.now(UTC)
    timeout_seconds = resolve_search_timeout_seconds(search_config)
    cache_ttl_ms = resolve_search_cache_ttl_ms(search_config)

    if brave_mode == "llm-context":
        llm_result = await _run_brave_llm_context_search(
            {
                "base_url": brave_base_url,
                "query": query,
                "api_key": api_key,
                "timeout_seconds": timeout_seconds,
                "diagnostics": diagnostics,
                "country": country,
                "search_lang": normalized_language.get("search_lang"),
                "freshness": freshness,
                "dateAfter": date_after,
                "dateBefore": date_before,
            }
        )
        results = llm_result["results"]
        payload = {
            "query": query,
            "provider": "brave",
            "mode": "llm-context",
            "count": len(results),
            "tookMs": int((datetime.now(UTC) - start).total_seconds() * 1000),
            "externalContent": {
                "untrusted": True,
                "source": "web_search",
                "provider": "brave",
                "wrapped": True,
            },
            "results": [
                {
                    "title": wrap_web_content(entry["title"], "web_search") if entry.get("title") else "",
                    "url": entry["url"],
                    "snippets": [
                        wrap_web_content(snippet, "web_search") for snippet in entry.get("snippets", [])
                    ],
                    **({"siteName": entry["siteName"]} if entry.get("siteName") else {}),
                }
                for entry in results
            ],
            **({"sources": llm_result["sources"]} if llm_result.get("sources") is not None else {}),
        }
        write_cached_search_payload(cache_key, payload, cache_ttl_ms)
        _log_brave_http(
            diagnostics,
            "cache write",
            {
                "mode": "llm-context",
                "query": query,
                "cacheKey": cache_key,
                "ttlMs": cache_ttl_ms,
                "count": len(results),
            },
        )
        return payload

    results = await _run_brave_web_search(
        {
            "base_url": brave_base_url,
            "query": query,
            "count": resolve_search_count(count, DEFAULT_SEARCH_COUNT),
            "api_key": api_key,
            "timeout_seconds": timeout_seconds,
            "diagnostics": diagnostics,
            "country": country,
            "search_lang": normalized_language.get("search_lang"),
            "ui_lang": normalized_language.get("ui_lang"),
            "freshness": freshness,
            "dateAfter": date_after,
            "dateBefore": date_before,
        }
    )
    payload = {
        "query": query,
        "provider": "brave",
        "count": len(results),
        "tookMs": int((datetime.now(UTC) - start).total_seconds() * 1000),
        "externalContent": {
            "untrusted": True,
            "source": "web_search",
            "provider": "brave",
            "wrapped": True,
        },
        "results": results,
    }
    write_cached_search_payload(cache_key, payload, cache_ttl_ms)
    _log_brave_http(
        diagnostics,
        "cache write",
        {
            "mode": "web",
            "query": query,
            "cacheKey": cache_key,
            "ttlMs": cache_ttl_ms,
            "count": len(results),
        },
    )
    return payload
