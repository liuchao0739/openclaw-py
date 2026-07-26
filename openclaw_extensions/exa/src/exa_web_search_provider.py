"""Exa provider module implements model/runtime integration."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.exa.src.exa_web_search_provider_shared import (
    create_exa_web_search_provider_base,
)

EXA_SEARCH_TYPES = ["auto", "neural", "fast", "deep", "deep-reasoning", "instant"]
EXA_FRESHNESS_VALUES = ["day", "week", "month", "year"]
EXA_MAX_SEARCH_COUNT = 100

EXA_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query string."},
        "count": {
            "type": "integer",
            "description": (
                "Number of results to return (1-100, subject to Exa search-type limits)."
            ),
            "minimum": 1,
            "maximum": EXA_MAX_SEARCH_COUNT,
        },
        "freshness": {
            "type": "string",
            "enum": list(EXA_FRESHNESS_VALUES),
            "description": 'Filter by time: "day", "week", "month", or "year".',
        },
        "date_after": {
            "type": "string",
            "description": "Only results published after this date (YYYY-MM-DD).",
        },
        "date_before": {
            "type": "string",
            "description": "Only results published before this date (YYYY-MM-DD).",
        },
        "type": {
            "type": "string",
            "enum": list(EXA_SEARCH_TYPES),
            "description": (
                'Exa search mode: "auto", "neural", "fast", "deep", '
                '"deep-reasoning", or "instant".'
            ),
        },
        "contents": {
            "type": "object",
            "properties": {
                "highlights": {
                    "description": (
                        "Highlights config: true, or an object with maxCharacters, "
                        "query, numSentences, or highlightsPerUrl."
                    ),
                },
                "text": {
                    "description": "Text config: true, or an object with maxCharacters.",
                },
                "summary": {
                    "description": "Summary config: true, or an object with query.",
                },
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}

_exa_runtime_module: Any | None = None


async def _load_exa_web_search_runtime():
    global _exa_runtime_module
    if _exa_runtime_module is None:
        from openclaw_extensions.exa.src import exa_web_search_provider_runtime

        _exa_runtime_module = exa_web_search_provider_runtime
    return _exa_runtime_module


def create_exa_web_search_provider() -> dict[str, Any]:
    def create_tool(ctx: dict[str, Any]) -> dict[str, Any]:
        async def execute(args: dict[str, Any]) -> dict[str, Any]:
            runtime = await _load_exa_web_search_runtime()
            return await runtime.execute_exa_web_search_provider_tool(ctx, args)

        return {
            "description": (
                "Search the web using Exa AI. Supports neural or keyword search, "
                "publication date filters, and optional highlights or text extraction."
            ),
            "parameters": EXA_SEARCH_SCHEMA,
            "execute": execute,
        }

    return {
        **create_exa_web_search_provider_base(),
        "create_tool": create_tool,
    }
