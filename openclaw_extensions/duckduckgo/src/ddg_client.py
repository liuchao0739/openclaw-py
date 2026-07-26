"""DuckDuckGo plugin module implements ddg client behavior."""

from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from openclaw.plugin_sdk.provider_http import read_provider_text_response
from openclaw.plugin_sdk.provider_web_search import (
    DEFAULT_CACHE_TTL_MINUTES,
    DEFAULT_SEARCH_COUNT,
    normalize_cache_key,
    read_cache,
    read_response_text,
    resolve_cache_ttl_ms,
    resolve_search_count,
    resolve_site_name,
    resolve_timeout_seconds,
    with_trusted_web_search_endpoint,
    write_cache,
)
from openclaw.security.external_content import wrap_web_content
from openclaw_extensions.duckduckgo.src.config import (
    DdgSafeSearch,
    resolve_ddg_region,
    resolve_ddg_safe_search,
)

DDG_HTML_ENDPOINT = "https://html.duckduckgo.com/html"
DEFAULT_TIMEOUT_SECONDS = 20
DDG_SAFE_SEARCH_PARAM: dict[DdgSafeSearch, str] = {
    "strict": "1",
    "moderate": "-1",
    "off": "-2",
}

DDG_SEARCH_CACHE: dict[str, dict[str, Any]] = {}


def decode_html_entities(text: str) -> str:
    def replace_entity(match: re.Match[str]) -> str:
        entity = match.group(0)
        normalized = entity.lower()
        if normalized == "&lt;":
            return "<"
        if normalized == "&gt;":
            return ">"
        if normalized == "&quot;":
            return '"'
        if normalized in ("&apos;", "&#39;", "&#x27;"):
            return "'"
        if normalized == "&#x2f;":
            return "/"
        if normalized == "&nbsp;":
            return " "
        if normalized == "&ndash;":
            return "-"
        if normalized == "&mdash;":
            return "--"
        if normalized == "&hellip;":
            return "..."
        if normalized == "&amp;":
            return "&"
        if normalized.startswith("&#x"):
            return chr(int(normalized[3:-1], 16))
        if normalized.startswith("&#"):
            return chr(int(normalized[2:-1], 10))
        return entity

    return re.sub(
        r"&(?:lt|gt|quot|apos|#39|#x27|#x2F|nbsp|ndash|mdash|hellip|amp|#\d+|#x[0-9a-f]+);",
        replace_entity,
        text,
        flags=re.IGNORECASE,
    )


def strip_html(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def decode_duck_duck_go_url(raw_url: str) -> str:
    try:
        normalized = f"https:{raw_url}" if raw_url.startswith("//") else raw_url
        parsed = urlparse(normalized)
        uddg = parse_qs(parsed.query).get("uddg", [None])[0]
        if uddg:
            return uddg
    except ValueError:
        pass
    return raw_url


def _read_href_attribute(tag_attributes: str) -> str:
    match = re.search(r'\bhref="([^"]*)"', tag_attributes, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def is_bot_challenge(html: str) -> bool:
    if re.search(r'class="[^"]*\bresult__a\b[^"]*"', html, flags=re.IGNORECASE):
        return False
    return bool(
        re.search(
            r"g-recaptcha|are you a human|id=\"challenge-form\"|name=\"challenge\"",
            html,
            flags=re.IGNORECASE,
        )
    )


async def read_duck_duck_go_html_response(response: Any) -> str:
    return await read_provider_text_response(response, "DuckDuckGo search")


def parse_duck_duck_go_html(html: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    result_regex = re.compile(
        r'<a\b(?=[^>]*\bclass="[^"]*\bresult__a\b[^"]*")([^>]*)>([\s\S]*?)</a>',
        flags=re.IGNORECASE,
    )
    next_result_regex = re.compile(
        r'<a\b(?=[^>]*\bclass="[^"]*\bresult__a\b[^"]*")[^>]*>',
        flags=re.IGNORECASE,
    )
    snippet_regex = re.compile(
        r'<a\b(?=[^>]*\bclass="[^"]*\bresult__snippet\b[^"]*")[^>]*>([\s\S]*?)</a>',
        flags=re.IGNORECASE,
    )

    for match in result_regex.finditer(html):
        raw_attributes = match.group(1) or ""
        raw_title = match.group(2) or ""
        raw_url = _read_href_attribute(raw_attributes)
        match_end = match.end()
        trailing_html = html[match_end:]
        next_result = next_result_regex.search(trailing_html)
        scoped_trailing_html = (
            trailing_html[: next_result.start()] if next_result else trailing_html
        )
        snippet_match = snippet_regex.search(scoped_trailing_html)
        raw_snippet = snippet_match.group(1) if snippet_match else ""
        title = decode_html_entities(strip_html(raw_title))
        url = decode_duck_duck_go_url(decode_html_entities(raw_url))
        snippet = decode_html_entities(strip_html(raw_snippet))
        if title and url:
            results.append({"title": title, "url": url, "snippet": snippet})
    return results


async def run_duck_duck_go_search(params: dict[str, Any]) -> dict[str, Any]:
    count = resolve_search_count(params.get("count"), DEFAULT_SEARCH_COUNT)
    region = params.get("region") or resolve_ddg_region(params.get("config"))
    safe_search_param = params.get("safeSearch") or params.get("safe_search")
    if safe_search_param in ("strict", "moderate", "off"):
        safe_search: DdgSafeSearch = safe_search_param
    else:
        safe_search = resolve_ddg_safe_search(params.get("config"))
    timeout_seconds = resolve_timeout_seconds(params.get("timeoutSeconds"), DEFAULT_TIMEOUT_SECONDS)
    cache_ttl_ms = resolve_cache_ttl_ms(params.get("cacheTtlMinutes"), DEFAULT_CACHE_TTL_MINUTES)
    cache_key = normalize_cache_key(
        json.dumps(
            {
                "provider": "duckduckgo",
                "query": params["query"],
                "count": count,
                "region": region or "",
                "safeSearch": safe_search,
            },
            sort_keys=True,
        )
    )
    cached = read_cache(DDG_SEARCH_CACHE, cache_key)
    if cached:
        payload = dict(cached["value"])
        payload["cached"] = True
        return payload

    query_params: dict[str, str] = {
        "q": params["query"],
        "kp": DDG_SAFE_SEARCH_PARAM[safe_search],
    }
    if region:
        query_params["kl"] = region
    url = f"{DDG_HTML_ENDPOINT}?{urlencode(query_params)}"

    started_at = time.time() * 1000

    async def handle_response(response: httpx.Response) -> list[dict[str, str]]:
        if response.status_code < 200 or response.status_code >= 300:
            detail = (await read_response_text(response, max_bytes=64_000))["text"]
            raise RuntimeError(
                f"DuckDuckGo search error ({response.status_code}): "
                f"{detail or response.reason_phrase}"
            )
        html = await read_duck_duck_go_html_response(response)
        if is_bot_challenge(html):
            raise RuntimeError("DuckDuckGo returned a bot-detection challenge.")
        return parse_duck_duck_go_html(html)[:count]

    results = await with_trusted_web_search_endpoint(
        {
            "url": url,
            "timeout_seconds": timeout_seconds,
            "init": {
                "method": "GET",
                "headers": {
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                    ),
                },
            },
        },
        handle_response,
    )

    payload = {
        "query": params["query"],
        "provider": "duckduckgo",
        "count": len(results),
        "tookMs": round(time.time() * 1000 - started_at),
        "externalContent": {
            "untrusted": True,
            "source": "web_search",
            "provider": "duckduckgo",
            "wrapped": True,
        },
        "results": [
            {
                "title": wrap_web_content(result["title"], "web_search"),
                "url": result["url"],
                "snippet": wrap_web_content(result["snippet"], "web_search")
                if result.get("snippet")
                else "",
                "siteName": resolve_site_name(result["url"]) or None,
            }
            for result in results
        ],
    }
    write_cache(DDG_SEARCH_CACHE, cache_key, payload, cache_ttl_ms)
    return payload


testing = {
    "decode_duck_duck_go_url": decode_duck_duck_go_url,
    "decode_html_entities": decode_html_entities,
    "is_bot_challenge": is_bot_challenge,
    "parse_duck_duck_go_html": parse_duck_duck_go_html,
    "read_duck_duck_go_html_response": read_duck_duck_go_html_response,
}

__testing = testing
