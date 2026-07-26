"""Firecrawl plugin module implements firecrawl client behavior."""

from __future__ import annotations

import ipaddress
import json
import math
import re
import time
from collections.abc import Awaitable, Callable
from typing import Any, Literal
from urllib.parse import urlparse, urlunparse

from openclaw.packages.normalization_core import is_record
from openclaw.plugin_sdk.provider_http import read_response_with_limit
from openclaw.plugin_sdk.provider_web_search import (
    DEFAULT_CACHE_TTL_MINUTES,
    normalize_cache_key,
    read_cache,
    read_response_text,
    resolve_cache_ttl_ms,
    resolve_site_name,
    with_trusted_web_search_endpoint,
    write_cache,
)
from openclaw.security.external_content import wrap_external_content, wrap_web_content
from openclaw.utils.normalize_secret_input import normalize_secret_input
from openclaw_extensions.firecrawl.src.config import (
    DEFAULT_FIRECRAWL_BASE_URL,
    resolve_firecrawl_api_key,
    resolve_firecrawl_base_url,
    resolve_firecrawl_max_age_ms,
    resolve_firecrawl_only_main_content,
    resolve_firecrawl_scrape_timeout_seconds,
    resolve_firecrawl_search_timeout_seconds,
)

SEARCH_CACHE: dict[str, dict[str, Any]] = {}
SCRAPE_CACHE: dict[str, dict[str, Any]] = {}
DEFAULT_SEARCH_COUNT = 5
DEFAULT_SCRAPE_MAX_CHARS = 50_000
FIRECRAWL_SCRAPE_RESPONSE_MAX_BYTES = 64 * 1024 * 1024
ALLOWED_FIRECRAWL_HOSTS = {"api.firecrawl.dev"}
FIRECRAWL_SELF_HOSTED_PRIVATE_ERROR = (
    "Firecrawl custom baseUrl must target a private or internal self-hosted endpoint."
)
FIRECRAWL_HTTP_PRIVATE_ERROR = (
    "Firecrawl HTTP baseUrl must target a private or internal self-hosted endpoint. "
    "Use https:// for public hosts."
)
PROVIDER_JSON_RESPONSE_MAX_BYTES = 16 * 1024 * 1024

FirecrawlEndpointMode = Literal["selfHosted", "strict"]
LookupFn = Callable[[str], Awaitable[list[str]]]

_lookup_fn_override: LookupFn | None = None

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "0.0.0.0",
        "metadata.google.internal",
    }
)


class SsrfBlockedError(Exception):
    """Raised when a Firecrawl scrape target is blocked by SSRF policy."""


def _set_lookup_fn_override(lookup_fn: LookupFn | None) -> None:
    global _lookup_fn_override
    _lookup_fn_override = lookup_fn


def _is_private_ip_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


def is_blocked_hostname_or_ip(hostname: str) -> bool:
    if not hostname:
        return True
    lowered = hostname.lower().strip()
    if lowered.startswith("[") and lowered.endswith("]"):
        lowered = lowered[1:-1]
    if lowered in _BLOCKED_HOSTNAMES:
        return True
    if lowered.endswith((".local", ".internal")):
        return True
    try:
        ip = ipaddress.ip_address(lowered)
        return _is_private_ip_address(str(ip))
    except ValueError:
        pass
    return lowered == "169.254.169.254"


async def _resolve_pinned_hostname_with_policy(
    hostname: str,
    *,
    lookup_fn: LookupFn | None = None,
    allow_private_network: bool = False,
) -> dict[str, Any]:
    resolver = lookup_fn or _lookup_fn_override
    if resolver is None:
        import socket

        def _sync_lookup(host: str) -> list[str]:
            infos = socket.getaddrinfo(host, None)
            return [info[4][0] for info in infos]

        addresses = _sync_lookup(hostname)
    else:
        addresses = await resolver(hostname)
    if allow_private_network:
        return {"addresses": addresses}
    blocked = [address for address in addresses if is_blocked_hostname_or_ip(address)]
    if blocked:
        raise SsrfBlockedError(f"Blocked hostname resolution for {hostname}")
    return {"addresses": addresses}


def _normalize_whitespace(value: str) -> str:
    return (
        value.replace("\r", "")
        .replace(r"[ \t]+\n", "\n")
        .strip()
    )


def markdown_to_text(markdown: str) -> str:
    text = markdown
    text = re.sub(r"!\[[^\]]*]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)]\([^)]+\)", r"\1", text)
    text = re.sub(
        r"```[\s\S]*?```",
        lambda block: block.group(0).replace("```", "").split("\n", 1)[-1],
        text,
    )
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate_text(value: str, max_chars: int) -> dict[str, Any]:
    if len(value) <= max_chars:
        return {"text": value, "truncated": False}
    return {"text": value[:max_chars], "truncated": True}


async def read_firecrawl_json_response(
    response: Any,
    label: str,
    *,
    max_bytes: int | None = None,
) -> dict[str, Any]:
    limit = max_bytes if max_bytes is not None else PROVIDER_JSON_RESPONSE_MAX_BYTES

    def on_overflow(params: dict[str, int]) -> Exception:
        return RuntimeError(f"{label}: JSON response exceeds {params['maxBytes']} bytes")

    raw = await read_response_with_limit(response, limit, on_overflow=on_overflow)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as cause:
        raise RuntimeError(f"{label}: malformed JSON response") from cause
    if not isinstance(payload, dict):
        raise TypeError(f"{label}: malformed JSON response")
    return payload


def assert_firecrawl_scrape_target_allowed(url: str) -> None:
    try:
        parsed = urlparse(url)
    except ValueError as cause:
        raise SsrfBlockedError("Invalid URL supplied to Firecrawl scrape") from cause
    if parsed.scheme not in ("http", "https"):
        if not parsed.scheme:
            raise SsrfBlockedError("Invalid URL supplied to Firecrawl scrape")
        raise SsrfBlockedError(
            f"Blocked non-HTTP(S) protocol in Firecrawl scrape URL: {parsed.scheme}"
        )
    if not parsed.netloc:
        raise SsrfBlockedError("Invalid URL supplied to Firecrawl scrape")
    if is_blocked_hostname_or_ip(parsed.hostname or ""):
        raise SsrfBlockedError(
            "Blocked hostname or private/internal IP in Firecrawl scrape URL: "
            f"{parsed.hostname}"
        )


def _is_official_firecrawl_endpoint(url: urlparse) -> bool:
    return url.scheme == "https" and url.hostname in ALLOWED_FIRECRAWL_HOSTS


async def _firecrawl_endpoint_targets_private_network(
    url: urlparse,
    lookup_fn: LookupFn | None = None,
) -> bool:
    hostname = url.hostname or ""
    if is_blocked_hostname_or_ip(hostname):
        return True
    try:
        pinned = await _resolve_pinned_hostname_with_policy(
            hostname,
            lookup_fn=lookup_fn,
            allow_private_network=True,
        )
        addresses = pinned["addresses"]
        return bool(addresses) and all(_is_private_ip_address(address) for address in addresses)
    except (OSError, ValueError):
        return False


async def validate_firecrawl_base_url(
    base_url: str,
    lookup_fn: LookupFn | None = None,
) -> FirecrawlEndpointMode:
    try:
        url = urlparse((base_url or DEFAULT_FIRECRAWL_BASE_URL).strip())
    except ValueError as cause:
        raise ValueError("Firecrawl baseUrl must be a valid http:// or https:// URL.") from cause
    if url.scheme not in ("http", "https"):
        raise ValueError("Firecrawl baseUrl must use http:// or https://.")
    if _is_official_firecrawl_endpoint(url):
        return "strict"
    is_private_target = await _firecrawl_endpoint_targets_private_network(url, lookup_fn)
    if is_private_target:
        return "selfHosted"
    if url.scheme == "http":
        raise ValueError(FIRECRAWL_HTTP_PRIVATE_ERROR)
    raise ValueError(f"{FIRECRAWL_SELF_HOSTED_PRIVATE_ERROR} Host: {url.hostname}")


async def resolve_endpoint(
    base_url: str,
    pathname: Literal["/v2/search", "/v2/scrape"],
    lookup_fn: LookupFn | None = None,
) -> dict[str, Any]:
    parsed = urlparse((base_url or DEFAULT_FIRECRAWL_BASE_URL).strip())
    mode = await validate_firecrawl_base_url(urlunparse(parsed), lookup_fn)
    return {
        "url": urlunparse((parsed.scheme, parsed.netloc, pathname, "", "", "")),
        "mode": mode,
    }


async def post_firecrawl_json(
    params: dict[str, Any],
    parse: Callable[[Any], Awaitable[Any]],
) -> Any:
    api_key = normalize_secret_input(params.get("apiKey") or "")
    mode = params.get("mode") or await validate_firecrawl_base_url(params["url"])
    headers = {
        "Content-Type": "application/json",
        **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
    }
    init = {
        "method": "POST",
        "headers": headers,
        "body": json.dumps(params["body"]),
    }
    request_params = {
        "url": params["url"],
        "timeout_seconds": params["timeoutSeconds"],
        "init": init,
    }

    async def run(response: Any) -> Any:
        if not getattr(response, "is_success", getattr(response, "ok", False)):
            detail = (
                getattr(response, "reason_phrase", None)
                or getattr(response, "status_text", None)
                or "request failed"
            )
            if isinstance(detail, str):
                detail = detail.strip() or "request failed"
            payload = None
            clone = getattr(response, "clone", None)
            json_response = clone() if callable(clone) else response
            try:
                body = await read_response_text(json_response, max_bytes=64_000)
                parsed_payload = json.loads(body["text"])
                if isinstance(parsed_payload, dict):
                    payload = parsed_payload
            except (json.JSONDecodeError, TypeError, ValueError):
                payload = None
            if payload:
                detail = (
                    payload.get("error")
                    if isinstance(payload.get("error"), str)
                    else payload.get("message")
                    if isinstance(payload.get("message"), str)
                    else detail
                )
            else:
                error_body = await read_response_text(response, max_bytes=64_000)
                if error_body["text"]:
                    detail = error_body["text"]
            safe_detail = wrap_web_content(str(detail)[:1_000], "web_fetch")
            status = getattr(response, "status_code", getattr(response, "status", 0))
            raise RuntimeError(f"{params['errorLabel']} API error ({status}): {safe_detail}")
        return await parse(response)

    if mode == "selfHosted":
        return await with_trusted_web_search_endpoint(request_params, run)
    return await with_trusted_web_search_endpoint(request_params, run)


def resolve_search_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    candidates = [
        payload.get("data"),
        payload.get("results"),
        data.get("results") if is_record(data) else None,
        data.get("data") if is_record(data) else None,
        data.get("web") if is_record(data) else None,
        payload.get("web", {}).get("results") if is_record(payload.get("web")) else None,
    ]
    raw_items = next((candidate for candidate in candidates if isinstance(candidate, list)), None)
    if not isinstance(raw_items, list):
        return []
    items: list[dict[str, Any]] = []
    for entry in raw_items:
        if not is_record(entry):
            continue
        metadata = entry.get("metadata") if is_record(entry.get("metadata")) else {}
        url = (
            entry.get("url")
            if isinstance(entry.get("url"), str) and entry.get("url")
            else entry.get("sourceURL")
            if isinstance(entry.get("sourceURL"), str) and entry.get("sourceURL")
            else entry.get("sourceUrl")
            if isinstance(entry.get("sourceUrl"), str) and entry.get("sourceUrl")
            else metadata.get("sourceURL")
            if isinstance(metadata.get("sourceURL"), str)
            else ""
        )
        if not url:
            continue
        title = (
            entry.get("title")
            if isinstance(entry.get("title"), str) and entry.get("title")
            else metadata.get("title")
            if isinstance(metadata.get("title"), str)
            else ""
        )
        description = (
            entry.get("description")
            if isinstance(entry.get("description"), str)
            else entry.get("snippet")
            if isinstance(entry.get("snippet"), str)
            else entry.get("summary")
            if isinstance(entry.get("summary"), str)
            else None
        )
        content = (
            entry.get("markdown")
            if isinstance(entry.get("markdown"), str)
            else entry.get("content")
            if isinstance(entry.get("content"), str)
            else entry.get("text")
            if isinstance(entry.get("text"), str)
            else None
        )
        published = (
            entry.get("publishedDate")
            if isinstance(entry.get("publishedDate"), str)
            else entry.get("published")
            if isinstance(entry.get("published"), str)
            else metadata.get("publishedTime")
            if isinstance(metadata.get("publishedTime"), str)
            else metadata.get("publishedDate")
            if isinstance(metadata.get("publishedDate"), str)
            else None
        )
        site_name = resolve_site_name(url)
        if site_name and site_name.startswith("www."):
            site_name = site_name[4:]
        items.append(
            {
                "title": title,
                "url": url,
                "description": description,
                "content": content,
                "published": published,
                "siteName": site_name,
            }
        )
    return items


def _build_search_payload(
    *,
    query: str,
    provider: str,
    items: list[dict[str, Any]],
    took_ms: int,
    scrape_results: bool,
) -> dict[str, Any]:
    return {
        "query": query,
        "provider": provider,
        "count": len(items),
        "tookMs": took_ms,
        "externalContent": {
            "untrusted": True,
            "source": "web_search",
            "provider": provider,
            "wrapped": True,
        },
        "results": [
            {
                "title": wrap_web_content(entry["title"], "web_search") if entry.get("title") else "",
                "url": entry["url"],
                "description": wrap_web_content(entry["description"], "web_search")
                if entry.get("description")
                else "",
                **({"published": entry["published"]} if entry.get("published") else {}),
                **({"siteName": entry["siteName"]} if entry.get("siteName") else {}),
                **(
                    {"content": wrap_web_content(entry["content"], "web_search")}
                    if scrape_results and entry.get("content")
                    else {}
                ),
            }
            for entry in items
        ],
    }


async def run_firecrawl_search(params: dict[str, Any]) -> dict[str, Any]:
    cfg = params.get("cfg")
    api_key = resolve_firecrawl_api_key(cfg)
    if not api_key:
        raise RuntimeError(
            "web_search (firecrawl) needs a Firecrawl API key. Set FIRECRAWL_API_KEY in the "
            "Gateway environment, or configure plugins.entries.firecrawl.config.webSearch.apiKey."
        )
    count = params.get("count")
    if isinstance(count, (int, float)) and math.isfinite(count):
        resolved_count = max(1, min(10, int(count)))
    else:
        resolved_count = DEFAULT_SEARCH_COUNT
    timeout_seconds = resolve_firecrawl_search_timeout_seconds(params.get("timeoutSeconds"))
    scrape_results = params.get("scrapeResults") is True
    sources = [item for item in (params.get("sources") or []) if item]
    categories = [item for item in (params.get("categories") or []) if item]
    base_url = resolve_firecrawl_base_url(cfg)
    cache_key = normalize_cache_key(
        json.dumps(
            {
                "type": "firecrawl-search",
                "q": params.get("query"),
                "count": resolved_count,
                "baseUrl": base_url,
                "sources": sources,
                "categories": categories,
                "scrapeResults": scrape_results,
            }
        )
    )
    cached = read_cache(SEARCH_CACHE, cache_key)
    if cached:
        return {**cached["value"], "cached": True}

    body: dict[str, Any] = {"query": params.get("query"), "limit": resolved_count}
    if sources:
        body["sources"] = sources
    if categories:
        body["categories"] = categories
    if scrape_results:
        body["scrapeOptions"] = {"formats": ["markdown"]}

    start = time.time() * 1000
    endpoint = await resolve_endpoint(base_url, "/v2/search")
    payload = await post_firecrawl_json(
        {
            "url": endpoint["url"],
            "mode": endpoint["mode"],
            "timeoutSeconds": timeout_seconds,
            "apiKey": api_key,
            "body": body,
            "errorLabel": "Firecrawl Search",
        },
        lambda response: read_firecrawl_json_response(response, "Firecrawl Search API error"),
    )
    if payload.get("success") is False:
        error = (
            payload.get("error")
            if isinstance(payload.get("error"), str)
            else payload.get("message")
            if isinstance(payload.get("message"), str)
            else "unknown error"
        )
        raise RuntimeError(f"Firecrawl Search API error: {error}")
    result = _build_search_payload(
        query=str(params.get("query") or ""),
        provider="firecrawl",
        items=resolve_search_items(payload),
        took_ms=int(time.time() * 1000 - start),
        scrape_results=scrape_results,
    )
    write_cache(
        SEARCH_CACHE,
        cache_key,
        result,
        resolve_cache_ttl_ms(None, DEFAULT_CACHE_TTL_MINUTES),
    )
    return result


def _resolve_scrape_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    return dict(data) if is_record(data) else {}


def parse_firecrawl_scrape_payload(params: dict[str, Any]) -> dict[str, Any]:
    data = _resolve_scrape_data(params["payload"])
    metadata = data.get("metadata") if is_record(data.get("metadata")) else {}
    markdown = (
        data.get("markdown")
        if isinstance(data.get("markdown"), str) and data.get("markdown")
        else data.get("content")
        if isinstance(data.get("content"), str) and data.get("content")
        else ""
    )
    if not markdown:
        raise RuntimeError("Firecrawl scrape returned no content.")
    extract_mode = params["extractMode"]
    raw_text = markdown_to_text(markdown) if extract_mode == "text" else markdown
    truncated = truncate_text(raw_text, params["maxChars"])
    wrapped_text = wrap_external_content(
        truncated["text"],
        source="web_fetch",
        include_warning=False,
    )
    title = metadata.get("title") if isinstance(metadata.get("title"), str) and metadata.get("title") else None
    warning = (
        params["payload"].get("warning")
        if isinstance(params["payload"].get("warning"), str) and params["payload"].get("warning")
        else None
    )
    return {
        "url": params["url"],
        "finalUrl": (
            metadata.get("sourceURL")
            if isinstance(metadata.get("sourceURL"), str) and metadata.get("sourceURL")
            else data.get("url")
            if isinstance(data.get("url"), str) and data.get("url")
            else params["url"]
        ),
        "status": (
            metadata.get("statusCode")
            if isinstance(metadata.get("statusCode"), int)
            else data.get("statusCode")
            if isinstance(data.get("statusCode"), int)
            else None
        ),
        "title": wrap_external_content(title, source="web_fetch", include_warning=False)
        if title
        else None,
        "extractor": "firecrawl",
        "extractMode": extract_mode,
        "externalContent": {
            "untrusted": True,
            "source": "web_fetch",
            "wrapped": True,
        },
        "truncated": truncated["truncated"],
        "rawLength": len(raw_text),
        "wrappedLength": len(wrapped_text),
        "text": wrapped_text,
        "warning": wrap_external_content(warning, source="web_fetch", include_warning=False)
        if warning
        else None,
    }


async def run_firecrawl_scrape(params: dict[str, Any]) -> dict[str, Any]:
    assert_firecrawl_scrape_target_allowed(params["url"])

    cfg = params.get("cfg")
    api_key = resolve_firecrawl_api_key(cfg)
    if not api_key and params.get("access") != "keyless":
        raise RuntimeError(
            "firecrawl_scrape needs a Firecrawl API key. Set FIRECRAWL_API_KEY in the Gateway "
            "environment, or configure plugins.entries.firecrawl.config.webFetch.apiKey."
        )
    base_url = resolve_firecrawl_base_url(cfg)
    timeout_seconds = resolve_firecrawl_scrape_timeout_seconds(cfg, params.get("timeoutSeconds"))
    only_main_content = resolve_firecrawl_only_main_content(cfg, params.get("onlyMainContent"))
    max_age_ms = resolve_firecrawl_max_age_ms(cfg, params.get("maxAgeMs"))
    proxy = params.get("proxy") or "auto"
    store_in_cache = params.get("storeInCache") if params.get("storeInCache") is not None else True
    max_chars = params.get("maxChars")
    if isinstance(max_chars, (int, float)) and math.isfinite(max_chars) and max_chars > 0:
        resolved_max_chars = int(max_chars)
    else:
        resolved_max_chars = DEFAULT_SCRAPE_MAX_CHARS
    cache_key = normalize_cache_key(
        json.dumps(
            {
                "type": "firecrawl-scrape",
                "url": params["url"],
                "extractMode": params["extractMode"],
                "baseUrl": base_url,
                "onlyMainContent": only_main_content,
                "maxAgeMs": max_age_ms,
                "proxy": proxy,
                "storeInCache": store_in_cache,
                "maxChars": resolved_max_chars,
            }
        )
    )
    cached = read_cache(SCRAPE_CACHE, cache_key)
    if cached:
        return {**cached["value"], "cached": True}

    endpoint = await resolve_endpoint(base_url, "/v2/scrape")

    async def parse_response(response: Any) -> dict[str, Any]:
        payload_local = await read_firecrawl_json_response(
            response,
            "Firecrawl fetch failed",
            max_bytes=FIRECRAWL_SCRAPE_RESPONSE_MAX_BYTES,
        )
        if payload_local.get("success") is False:
            detail = (
                payload_local.get("error")
                if isinstance(payload_local.get("error"), str)
                else payload_local.get("message")
                if isinstance(payload_local.get("message"), str)
                else getattr(response, "reason_phrase", "")
            )
            status = getattr(response, "status_code", getattr(response, "status", 0))
            raise RuntimeError(
                f"Firecrawl fetch failed ({status}): "
                f"{wrap_web_content(str(detail), 'web_fetch')}".strip()
            )
        return payload_local

    payload = await post_firecrawl_json(
        {
            "url": endpoint["url"],
            "mode": endpoint["mode"],
            "timeoutSeconds": timeout_seconds,
            "apiKey": api_key,
            "errorLabel": "Firecrawl",
            "body": {
                "url": params["url"],
                "formats": ["markdown"],
                "onlyMainContent": only_main_content,
                "timeout": timeout_seconds * 1000,
                "maxAge": max_age_ms,
                "proxy": proxy,
                "storeInCache": store_in_cache,
            },
        },
        parse_response,
    )
    result = parse_firecrawl_scrape_payload(
        {
            "payload": payload,
            "url": params["url"],
            "extractMode": params["extractMode"],
            "maxChars": resolved_max_chars,
        }
    )
    write_cache(
        SCRAPE_CACHE,
        cache_key,
        result,
        resolve_cache_ttl_ms(None, DEFAULT_CACHE_TTL_MINUTES),
    )
    return result


testing = {
    "assert_firecrawl_scrape_target_allowed": assert_firecrawl_scrape_target_allowed,
    "parse_firecrawl_scrape_payload": parse_firecrawl_scrape_payload,
    "post_firecrawl_json": post_firecrawl_json,
    "read_firecrawl_json_response": read_firecrawl_json_response,
    "resolve_endpoint": resolve_endpoint,
    "validate_firecrawl_base_url": validate_firecrawl_base_url,
    "resolve_search_items": resolve_search_items,
    "set_lookup_fn_override": _set_lookup_fn_override,
}

__testing = testing

__all__ = [
    "__testing",
    "assert_firecrawl_scrape_target_allowed",
    "parse_firecrawl_scrape_payload",
    "post_firecrawl_json",
    "read_firecrawl_json_response",
    "resolve_endpoint",
    "resolve_search_items",
    "run_firecrawl_scrape",
    "run_firecrawl_search",
    "testing",
    "validate_firecrawl_base_url",
]
