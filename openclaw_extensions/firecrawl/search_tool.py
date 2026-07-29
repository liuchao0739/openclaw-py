from typing import Any, Optional

from .._sdk import (
    json_result,
    read_positive_integer_param,
    read_string_array_param,
    read_string_param,
)
from .client import FirecrawlSearchParams, run_firecrawl_search

FIRECRAWL_SEARCH_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query string."},
        "count": {
            "type": "integer",
            "description": "Number of results to return (1-10).",
            "minimum": 1,
            "maximum": 10,
        },
        "sources": {
            "type": "array",
            "items": {"type": "string"},
            "description": 'Optional sources list, for example ["web"], ["news"], or ["images"].',
        },
        "categories": {
            "type": "array",
            "items": {"type": "string"},
            "description": 'Optional Firecrawl categories, for example ["github"] or ["research"].',
        },
        "scrapeResults": {
            "type": "boolean",
            "description": "Include scraped result content when Firecrawl returns it.",
        },
        "timeoutSeconds": {
            "type": "integer",
            "description": "Timeout in seconds for the Firecrawl Search request.",
            "minimum": 1,
        },
    },
    "additionalProperties": False,
}


def create_firecrawl_search_tool(api: dict) -> dict:
    async def execute(tool_call_id: str, raw_params: dict) -> dict:
        query = read_string_param(raw_params, "query", required=True)
        count = read_positive_integer_param(
            raw_params, "count", max=10, message="count must be an integer from 1 to 10"
        )
        timeout_seconds = read_positive_integer_param(raw_params, "timeoutSeconds")
        sources = read_string_array_param(raw_params, "sources")
        categories = read_string_array_param(raw_params, "categories")
        scrape_results = raw_params.get("scrapeResults") is True

        params = FirecrawlSearchParams(
            cfg=api["config"],
            query=query,
            count=count,
            timeout_seconds=timeout_seconds,
            sources=sources,
            categories=categories,
            scrape_results=scrape_results,
        )
        return json_result(await run_firecrawl_search(params))

    return {
        "name": "firecrawl_search",
        "label": "Firecrawl Search",
        "description": "Search the web using Firecrawl v2/search. Can optionally include scraped content from result pages.",
        "parameters": FIRECRAWL_SEARCH_TOOL_SCHEMA,
        "execute": execute,
    }
