"""Exa provider module implements model/runtime integration."""

from __future__ import annotations

import json
import math
import re
import time
from calendar import monthrange
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from openclaw.agents.tools.common import read_positive_integer_param, read_string_param
from openclaw.packages.normalization_core import (
    normalize_optional_lowercase_string,
    normalize_optional_string,
)
from openclaw.plugin_sdk.provider_http import read_response_with_limit
from openclaw.plugin_sdk.provider_web_search import (
    DEFAULT_SEARCH_COUNT,
    SearchConfigRecord,
    build_search_cache_key,
    merge_scoped_search_config,
    parse_iso_date_range,
    read_cached_search_payload,
    read_configured_secret_string,
    read_provider_env_value,
    read_response_text_limited,
    resolve_provider_web_search_plugin_config,
    resolve_search_cache_ttl_ms,
    resolve_search_timeout_seconds,
    resolve_site_name,
    with_trusted_web_search_endpoint,
    write_cached_search_payload,
)
from openclaw.security.external_content import wrap_web_content

EXA_SEARCH_ENDPOINT = "https://api.exa.ai/search"
EXA_SEARCH_TYPES = ["auto", "neural", "fast", "deep", "deep-reasoning", "instant"]
EXA_FRESHNESS_VALUES = ["day", "week", "month", "year"]
EXA_MAX_SEARCH_COUNT = 100
EXA_ERROR_BODY_LIMIT_BYTES = 8 * 1024
EXA_SEARCH_JSON_MAX_BYTES = 16 * 1024 * 1024


async def read_exa_search_results(
    response: Any,
    *,
    max_bytes: int | None = None,
) -> list[dict[str, Any]]:
    limit = max_bytes if max_bytes is not None else EXA_SEARCH_JSON_MAX_BYTES

    def on_overflow(params: dict[str, int]) -> Exception:
        return RuntimeError(f"Exa API response exceeds {params['maxBytes']} bytes")

    raw = await read_response_with_limit(response, limit, on_overflow=on_overflow)
    try:
        return normalize_exa_results(json.loads(raw.decode("utf-8")))
    except json.JSONDecodeError as cause:
        raise RuntimeError("Exa API returned malformed JSON") from cause


async def read_exa_error_detail(response: Any) -> str:
    return await read_response_text_limited(response, EXA_ERROR_BODY_LIMIT_BYTES)


def normalize_exa_freshness(value: str | None) -> str | None:
    trimmed = normalize_optional_lowercase_string(value)
    if not trimmed:
        return None
    return trimmed if trimmed in EXA_FRESHNESS_VALUES else None


def resolve_exa_config(search_config: SearchConfigRecord | None = None) -> dict[str, Any]:
    exa = search_config.get("exa") if search_config else None
    return dict(exa) if isinstance(exa, dict) and not isinstance(exa, list) else {}


def resolve_exa_api_key(exa: dict[str, Any] | None = None) -> str | None:
    return read_configured_secret_string(
        exa.get("apiKey") if exa else None,
        "tools.web.search.exa.apiKey",
    ) or read_provider_env_value(["EXA_API_KEY"])


def invalid_base_url_payload(value: str) -> dict[str, str]:
    return {
        "error": "invalid_base_url",
        "message": (
            "plugins.entries.exa.config.webSearch.baseUrl must be a valid http(s) URL. "
            f"Got: {value}"
        ),
        "docs": "https://docs.openclaw.ai/tools/exa-search",
    }


def resolve_exa_search_endpoint(
    exa: dict[str, Any] | None = None,
) -> dict[str, str]:
    configured = normalize_optional_string(exa.get("baseUrl") if exa else None)
    if not configured:
        return {"endpoint": EXA_SEARCH_ENDPOINT}

    if re.match(r"^[a-z][a-z0-9+.-]*://", configured, re.IGNORECASE) and not re.match(
        r"^https?://", configured, re.IGNORECASE
    ):
        return invalid_base_url_payload(configured)

    candidate = configured if re.match(r"^https?://", configured, re.IGNORECASE) else f"https://{configured}"
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return invalid_base_url_payload(configured)

    if parsed.scheme not in ("http", "https"):
        return invalid_base_url_payload(configured)

    pathname = parsed.path.rstrip("/")
    if pathname.endswith("/search"):
        new_path = pathname
    elif pathname:
        new_path = f"{pathname}/search"
    else:
        new_path = "/search"
    endpoint = urlunparse(
        (parsed.scheme, parsed.netloc, new_path, parsed.params, parsed.query, "")
    )
    return {"endpoint": endpoint}


def resolve_exa_description(result: dict[str, Any]) -> str:
    highlights = result.get("highlights")
    if isinstance(highlights, list):
        highlight_text = "\n".join(
            entry
            for entry in (normalize_optional_string(item) for item in highlights)
            if entry
        )
        if highlight_text:
            return highlight_text

    summary = normalize_optional_string(result.get("summary"))
    if summary:
        return summary

    return normalize_optional_string(result.get("text")) or ""


def _parse_positive_integer(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _parse_strict_integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or not re.fullmatch(r"[+-]?\d+", normalized):
        return None
    return int(normalized)


def _parse_strict_positive_integer(value: Any) -> int | None:
    parsed = _parse_strict_integer(value)
    return parsed if parsed is not None and parsed > 0 else None


def invalid_contents_payload(message: str) -> dict[str, str]:
    return {
        "error": "invalid_contents",
        "message": message,
        "docs": "https://docs.openclaw.ai/tools/web",
    }


def is_error_payload(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and "error" in value
        and "message" in value
        and "docs" in value
    )


def resolve_exa_search_count(value: Any, fallback: int) -> int:
    parsed = _parse_strict_positive_integer(value)
    if parsed is None:
        return fallback
    return min(EXA_MAX_SEARCH_COUNT, parsed)


def parse_exa_contents(raw_contents: Any) -> dict[str, Any]:
    if raw_contents is None:
        return {"value": None}

    if not isinstance(raw_contents, dict) or isinstance(raw_contents, list):
        return invalid_contents_payload(
            "contents must be an object with optional text, highlights, and summary fields."
        )

    allowed_keys = {"text", "highlights", "summary"}
    for key in raw_contents:
        if key not in allowed_keys:
            return invalid_contents_payload(
                f'contents has unknown field "{key}". Only "text", "highlights", and "summary" are allowed.'
            )

    parsed: dict[str, Any] = {}

    def parse_text(value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if not isinstance(value, dict) or isinstance(value, list):
            return invalid_contents_payload("contents.text must be a boolean or an object.")
        for key in value:
            if key != "maxCharacters":
                return invalid_contents_payload(
                    f'contents.text has unknown field "{key}". Only "maxCharacters" is allowed.'
                )
        if "maxCharacters" in value and _parse_positive_integer(value["maxCharacters"]) is None:
            return invalid_contents_payload("contents.text.maxCharacters must be a positive integer.")
        max_characters = _parse_positive_integer(value.get("maxCharacters"))
        return {"maxCharacters": max_characters} if max_characters else {}

    def parse_highlights(value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if not isinstance(value, dict) or isinstance(value, list):
            return invalid_contents_payload("contents.highlights must be a boolean or an object.")
        allowed = {"maxCharacters", "query", "numSentences", "highlightsPerUrl"}
        for key in value:
            if key not in allowed:
                return invalid_contents_payload(
                    f'contents.highlights has unknown field "{key}". Allowed fields are '
                    '"maxCharacters", "query", "numSentences", and "highlightsPerUrl".'
                )
        if "maxCharacters" in value and _parse_positive_integer(value["maxCharacters"]) is None:
            return invalid_contents_payload(
                "contents.highlights.maxCharacters must be a positive integer."
            )
        if "numSentences" in value and _parse_positive_integer(value["numSentences"]) is None:
            return invalid_contents_payload(
                "contents.highlights.numSentences must be a positive integer."
            )
        if "highlightsPerUrl" in value and _parse_positive_integer(value["highlightsPerUrl"]) is None:
            return invalid_contents_payload(
                "contents.highlights.highlightsPerUrl must be a positive integer."
            )
        if "query" in value and not isinstance(value["query"], str):
            return invalid_contents_payload("contents.highlights.query must be a string.")
        result: dict[str, Any] = {}
        max_characters = _parse_positive_integer(value.get("maxCharacters"))
        if max_characters:
            result["maxCharacters"] = max_characters
        if isinstance(value.get("query"), str):
            result["query"] = value["query"]
        num_sentences = _parse_positive_integer(value.get("numSentences"))
        if num_sentences:
            result["numSentences"] = num_sentences
        highlights_per_url = _parse_positive_integer(value.get("highlightsPerUrl"))
        if highlights_per_url:
            result["highlightsPerUrl"] = highlights_per_url
        return result

    def parse_summary(value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if not isinstance(value, dict) or isinstance(value, list):
            return invalid_contents_payload("contents.summary must be a boolean or an object.")
        for key in value:
            if key != "query":
                return invalid_contents_payload(
                    f'contents.summary has unknown field "{key}". Only "query" is allowed.'
                )
        if "query" in value and not isinstance(value["query"], str):
            return invalid_contents_payload("contents.summary.query must be a string.")
        return {"query": value["query"]} if isinstance(value.get("query"), str) else {}

    if "text" in raw_contents:
        parsed_text = parse_text(raw_contents["text"])
        if is_error_payload(parsed_text):
            return parsed_text
        parsed["text"] = parsed_text
    if "highlights" in raw_contents:
        parsed_highlights = parse_highlights(raw_contents["highlights"])
        if is_error_payload(parsed_highlights):
            return parsed_highlights
        parsed["highlights"] = parsed_highlights
    if "summary" in raw_contents:
        parsed_summary = parse_summary(raw_contents["summary"])
        if is_error_payload(parsed_summary):
            return parsed_summary
        parsed["summary"] = parsed_summary

    return {"value": parsed}


def normalize_exa_results(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    results = payload.get("results")
    if not isinstance(results, list):
        return []
    return [
        entry
        for entry in results
        if isinstance(entry, dict) and not isinstance(entry, list)
    ]


def resolve_freshness_start_date(freshness: str) -> str:
    now = datetime.now(UTC)
    if freshness == "day":
        return (now - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    if freshness == "week":
        return (now - timedelta(days=7)).isoformat().replace("+00:00", "Z")
    if freshness == "month":
        current_day = now.day
        first_of_month = now.replace(day=1)
        if first_of_month.month == 1:
            target = first_of_month.replace(year=first_of_month.year - 1, month=12)
        else:
            target = first_of_month.replace(month=first_of_month.month - 1)
        last_day = monthrange(target.year, target.month)[1]
        target = target.replace(day=min(current_day, last_day))
        return target.isoformat().replace("+00:00", "Z")
    target = now.replace(year=now.year - 1)
    return target.isoformat().replace("+00:00", "Z")


async def run_exa_search(params: dict[str, Any]) -> list[dict[str, Any]]:
    body: dict[str, Any] = {
        "query": params["query"],
        "numResults": params["count"],
        "type": params["type"],
        "contents": params.get("contents") or {"highlights": True},
    }

    if params.get("dateAfter"):
        body["startPublishedDate"] = params["dateAfter"]
    elif params.get("freshness"):
        body["startPublishedDate"] = resolve_freshness_start_date(params["freshness"])
    if params.get("dateBefore"):
        body["endPublishedDate"] = params["dateBefore"]

    async def handle_response(response: httpx.Response) -> list[dict[str, Any]]:
        if response.status_code < 200 or response.status_code >= 300:
            detail = await read_exa_error_detail(response)
            raise RuntimeError(
                f"Exa API error ({response.status_code}): {detail or response.reason_phrase}"
            )
        return await read_exa_search_results(response)

    return await with_trusted_web_search_endpoint(
        {
            "url": params["endpoint"],
            "timeout_seconds": params["timeoutSeconds"],
            "init": {
                "method": "POST",
                "headers": {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "x-api-key": params["apiKey"],
                    "x-exa-integration": "openclaw",
                },
                "body": json.dumps(body),
            },
        },
        handle_response,
    )


def missing_exa_key_payload() -> dict[str, str]:
    return {
        "error": "missing_exa_api_key",
        "message": (
            "web_search (exa) needs an Exa API key. Set EXA_API_KEY in the Gateway "
            "environment, or configure tools.web.search.exa.apiKey."
        ),
        "docs": "https://docs.openclaw.ai/tools/web",
    }


def build_exa_cache_key(params: dict[str, Any]) -> str:
    contents = params.get("contents") or {}
    return build_search_cache_key(
        [
            "exa",
            params["endpoint"],
            params["type"],
            params["query"],
            params["count"],
            params.get("freshness"),
            params.get("dateAfter"),
            params.get("dateBefore"),
            json.dumps(contents.get("highlights")) if contents.get("highlights") else None,
            json.dumps(contents.get("text")) if contents.get("text") else None,
            json.dumps(contents.get("summary")) if contents.get("summary") else None,
        ]
    )


async def execute_exa_web_search_provider_tool(
    ctx: dict[str, Any],
    args: dict[str, Any],
) -> dict[str, Any]:
    search_config_raw = ctx.get("search_config") or ctx.get("searchConfig")
    search_config = merge_scoped_search_config(
        search_config_raw if isinstance(search_config_raw, dict) else None,
        "exa",
        resolve_provider_web_search_plugin_config(ctx.get("config"), "exa"),
    )
    exa_config = resolve_exa_config(search_config)
    api_key = resolve_exa_api_key(exa_config)
    if not api_key:
        return missing_exa_key_payload()

    endpoint_result = resolve_exa_search_endpoint(exa_config)
    if "error" in endpoint_result:
        return endpoint_result
    endpoint = endpoint_result["endpoint"]

    query = read_string_param(args, "query", required=True)
    raw_type = read_string_param(args, "type")
    search_type = raw_type if raw_type in EXA_SEARCH_TYPES else "auto"
    count = (
        read_positive_integer_param(
            args,
            "count",
            max_value=EXA_MAX_SEARCH_COUNT,
            message=f"count must be an integer from 1 to {EXA_MAX_SEARCH_COUNT}.",
        )
        or (search_config.get("maxResults") if search_config else None)
    )
    raw_freshness = read_string_param(args, "freshness")
    freshness = normalize_exa_freshness(raw_freshness)
    if raw_freshness and not freshness:
        return {
            "error": "invalid_freshness",
            "message": 'freshness must be one of "day", "week", "month", or "year".',
            "docs": "https://docs.openclaw.ai/tools/web",
        }

    raw_date_after = read_string_param(args, "date_after")
    raw_date_before = read_string_param(args, "date_before")
    if freshness and (raw_date_after or raw_date_before):
        return {
            "error": "conflicting_time_filters",
            "message": (
                "freshness cannot be combined with date_after or date_before. "
                "Use one time-filter mode."
            ),
            "docs": "https://docs.openclaw.ai/tools/web",
        }

    parsed_date_range = parse_iso_date_range(
        raw_date_after=raw_date_after,
        raw_date_before=raw_date_before,
        invalid_date_after_message="date_after must be YYYY-MM-DD format.",
        invalid_date_before_message="date_before must be YYYY-MM-DD format.",
        invalid_date_range_message="date_after must be earlier than or equal to date_before.",
    )
    if "error" in parsed_date_range:
        return parsed_date_range
    date_after = parsed_date_range.get("dateAfter")
    date_before = parsed_date_range.get("dateBefore")

    parsed_contents = parse_exa_contents(args.get("contents"))
    if is_error_payload(parsed_contents):
        return parsed_contents
    contents_value = parsed_contents.get("value")
    contents = contents_value if contents_value else None

    resolved_count = resolve_exa_search_count(count, DEFAULT_SEARCH_COUNT)
    cache_key = build_exa_cache_key(
        {
            "endpoint": endpoint,
            "type": search_type,
            "query": query,
            "count": resolved_count,
            "freshness": freshness,
            "dateAfter": date_after,
            "dateBefore": date_before,
            "contents": contents,
        }
    )
    cached = read_cached_search_payload(cache_key)
    if cached:
        return cached

    started_at = time.time() * 1000
    results = await run_exa_search(
        {
            "apiKey": api_key,
            "endpoint": endpoint,
            "query": query,
            "count": resolved_count,
            "freshness": freshness,
            "dateAfter": date_after,
            "dateBefore": date_before,
            "type": search_type,
            "contents": contents,
            "timeoutSeconds": resolve_search_timeout_seconds(search_config),
        }
    )

    payload = {
        "query": query,
        "provider": "exa",
        "count": len(results),
        "tookMs": round(time.time() * 1000 - started_at),
        "externalContent": {
            "untrusted": True,
            "source": "web_search",
            "provider": "exa",
            "wrapped": True,
        },
        "results": [
            _format_exa_result(entry)
            for entry in results
        ],
    }

    write_cached_search_payload(
        cache_key,
        payload,
        resolve_search_cache_ttl_ms(search_config),
    )
    return payload


def _format_exa_result(entry: dict[str, Any]) -> dict[str, Any]:
    title = entry.get("title") if isinstance(entry.get("title"), str) else ""
    url = entry.get("url") if isinstance(entry.get("url"), str) else ""
    description = resolve_exa_description(entry)
    summary = normalize_optional_string(entry.get("summary")) or ""
    highlight_scores = entry.get("highlightScores")
    scores = (
        [score for score in highlight_scores if isinstance(score, (int, float)) and math.isfinite(score)]
        if isinstance(highlight_scores, list)
        else []
    )
    published = (
        entry.get("publishedDate")
        if isinstance(entry.get("publishedDate"), str) and entry.get("publishedDate")
        else None
    )
    result: dict[str, Any] = {
        "title": wrap_web_content(title, "web_search") if title else "",
        "url": url,
        "description": wrap_web_content(description, "web_search") if description else "",
        "published": published,
        "siteName": resolve_site_name(url) or None,
    }
    if summary:
        result["summary"] = wrap_web_content(summary, "web_search")
    if scores:
        result["highlightScores"] = scores
    return result


testing = {
    "normalize_exa_results": normalize_exa_results,
    "normalize_exa_freshness": normalize_exa_freshness,
    "parse_exa_contents": parse_exa_contents,
    "build_exa_cache_key": build_exa_cache_key,
    "resolve_exa_api_key": resolve_exa_api_key,
    "resolve_exa_config": resolve_exa_config,
    "resolve_exa_description": resolve_exa_description,
    "resolve_exa_search_count": resolve_exa_search_count,
    "resolve_exa_search_endpoint": resolve_exa_search_endpoint,
    "resolve_freshness_start_date": resolve_freshness_start_date,
    "read_exa_error_detail": read_exa_error_detail,
    "read_exa_search_results": read_exa_search_results,
}

__testing = testing
