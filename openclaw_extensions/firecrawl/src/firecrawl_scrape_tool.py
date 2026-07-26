"""Firecrawl plugin module implements firecrawl scrape tool behavior."""

from __future__ import annotations

import json
from typing import Any

from openclaw.agents.tools.common import (
    ToolInputError,
    read_positive_integer_param,
    read_string_param,
)
from openclaw_extensions.firecrawl.src.firecrawl_client import run_firecrawl_scrape


def _read_non_negative_integer_param(
    params: dict[str, Any],
    key: str,
    *,
    message: str | None = None,
) -> int | None:
    raw = params.get(key)
    if raw is None:
        return None
    if isinstance(raw, bool):
        raise ToolInputError(message or f"{key} must be a non-negative integer")
    if isinstance(raw, int) and raw >= 0:
        return raw
    if isinstance(raw, float) and raw >= 0 and raw == int(raw):
        return int(raw)
    if isinstance(raw, str):
        trimmed = raw.strip()
        if not trimmed:
            return None
        try:
            parsed = float(trimmed)
        except ValueError as cause:
            raise ToolInputError(message or f"{key} must be a non-negative integer") from cause
        if parsed == int(parsed) and parsed >= 0:
            return int(parsed)
    raise ToolInputError(message or f"{key} must be a non-negative integer")


def _json_result(payload: Any) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
        "details": payload,
    }


def create_firecrawl_scrape_tool(api: Any) -> dict[str, Any]:
    async def execute(_tool_call_id: str, raw_params: dict[str, Any]) -> dict[str, Any]:
        url = read_string_param(raw_params, "url", required=True)
        extract_mode = "text" if read_string_param(raw_params, "extractMode") == "text" else "markdown"
        max_chars = read_positive_integer_param(raw_params, "maxChars")
        max_age_ms = _read_non_negative_integer_param(raw_params, "maxAgeMs")
        timeout_seconds = read_positive_integer_param(raw_params, "timeoutSeconds")
        proxy_raw = read_string_param(raw_params, "proxy")
        proxy = proxy_raw if proxy_raw in {"basic", "stealth", "auto"} else None
        only_main_content = (
            raw_params.get("onlyMainContent")
            if isinstance(raw_params.get("onlyMainContent"), bool)
            else None
        )
        store_in_cache = (
            raw_params.get("storeInCache") if isinstance(raw_params.get("storeInCache"), bool) else None
        )
        return _json_result(
            await run_firecrawl_scrape(
                {
                    "cfg": api.config,
                    "url": url or "",
                    "extractMode": extract_mode,
                    "maxChars": max_chars,
                    "onlyMainContent": only_main_content,
                    "maxAgeMs": max_age_ms,
                    "proxy": proxy,
                    "storeInCache": store_in_cache,
                    "timeoutSeconds": timeout_seconds,
                }
            )
        )

    return {
        "name": "firecrawl_scrape",
        "label": "Firecrawl Scrape",
        "description": (
            "Scrape a page using Firecrawl v2/scrape. Useful for JS-heavy or bot-protected pages "
            "where plain web_fetch is weak."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "HTTP or HTTPS URL to scrape via Firecrawl."},
                "extractMode": {
                    "type": "string",
                    "description": 'Extraction mode ("markdown" or "text"). Default: markdown.',
                },
                "maxChars": {
                    "type": "integer",
                    "description": "Maximum characters to return.",
                    "minimum": 100,
                },
                "onlyMainContent": {
                    "type": "boolean",
                    "description": "Keep only main content when Firecrawl supports it.",
                },
                "maxAgeMs": {
                    "type": "integer",
                    "description": "Maximum Firecrawl cache age in milliseconds.",
                    "minimum": 0,
                },
                "proxy": {
                    "type": "string",
                    "description": 'Firecrawl proxy mode ("auto", "basic", or "stealth").',
                },
                "storeInCache": {
                    "type": "boolean",
                    "description": "Whether Firecrawl should store the scrape in its cache.",
                },
                "timeoutSeconds": {
                    "type": "integer",
                    "description": "Timeout in seconds for the Firecrawl scrape request.",
                    "minimum": 1,
                },
            },
            "additionalProperties": False,
        },
        "execute": execute,
    }
