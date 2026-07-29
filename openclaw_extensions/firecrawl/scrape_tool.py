from typing import Any, Optional

from .._sdk import (
    json_result,
    read_non_negative_integer_param,
    read_positive_integer_param,
    read_string_param,
)
from .client import FirecrawlScrapeParams, run_firecrawl_scrape

FIRECRAWL_SCRAPE_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "HTTP or HTTPS URL to scrape via Firecrawl."},
        "extractMode": {
            "type": "string",
            "enum": ["markdown", "text"],
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
            "enum": ["auto", "basic", "stealth"],
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
}


def create_firecrawl_scrape_tool(api: dict) -> dict:
    async def execute(tool_call_id: str, raw_params: dict) -> dict:
        url = read_string_param(raw_params, "url", required=True)
        extract_mode = "text" if read_string_param(raw_params, "extractMode") == "text" else "markdown"
        max_chars = read_positive_integer_param(raw_params, "maxChars")
        max_age_ms = read_non_negative_integer_param(raw_params, "maxAgeMs")
        timeout_seconds = read_positive_integer_param(raw_params, "timeoutSeconds")
        proxy_raw = read_string_param(raw_params, "proxy")
        proxy = proxy_raw if proxy_raw in ("basic", "stealth", "auto") else None
        only_main_content = raw_params["onlyMainContent"] if isinstance(raw_params.get("onlyMainContent"), bool) else None
        store_in_cache = raw_params["storeInCache"] if isinstance(raw_params.get("storeInCache"), bool) else None

        params = FirecrawlScrapeParams(
            cfg=api["config"],
            url=url,
            extract_mode=extract_mode,
            max_chars=max_chars,
            only_main_content=only_main_content,
            max_age_ms=max_age_ms,
            proxy=proxy,
            store_in_cache=store_in_cache,
            timeout_seconds=timeout_seconds,
        )
        return json_result(await run_firecrawl_scrape(params))

    return {
        "name": "firecrawl_scrape",
        "label": "Firecrawl Scrape",
        "description": "Scrape a page using Firecrawl v2/scrape. Useful for JS-heavy or bot-protected pages where plain web_fetch is weak.",
        "parameters": FIRECRAWL_SCRAPE_TOOL_SCHEMA,
        "execute": execute,
    }
