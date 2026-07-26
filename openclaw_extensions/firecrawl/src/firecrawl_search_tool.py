"""Firecrawl plugin module implements firecrawl search tool behavior."""

from __future__ import annotations

import json
from typing import Any

from openclaw.agents.tools.common import read_positive_integer_param, read_string_param
from openclaw.plugin_sdk import read_string_array_param
from openclaw_extensions.firecrawl.src.firecrawl_client import run_firecrawl_search


def _json_result(payload: Any) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
        "details": payload,
    }


def create_firecrawl_search_tool(api: Any) -> dict[str, Any]:
    async def execute(_tool_call_id: str, raw_params: dict[str, Any]) -> dict[str, Any]:
        query = read_string_param(raw_params, "query", required=True)
        count = read_positive_integer_param(
            raw_params,
            "count",
            max_value=10,
            message="count must be an integer from 1 to 10",
        )
        timeout_seconds = read_positive_integer_param(raw_params, "timeoutSeconds")
        sources = read_string_array_param(raw_params, "sources") or []
        categories = read_string_array_param(raw_params, "categories") or []
        scrape_results = raw_params.get("scrapeResults") is True
        return _json_result(
            await run_firecrawl_search(
                {
                    "cfg": api.config,
                    "query": query or "",
                    "count": count,
                    "timeoutSeconds": timeout_seconds,
                    "sources": [item for item in sources if item],
                    "categories": [item for item in categories if item],
                    "scrapeResults": scrape_results,
                }
            )
        )

    return {
        "name": "firecrawl_search",
        "label": "Firecrawl Search",
        "description": (
            "Search the web using Firecrawl v2/search. Can optionally include scraped content "
            "from result pages."
        ),
        "parameters": {
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
        },
        "execute": execute,
    }
