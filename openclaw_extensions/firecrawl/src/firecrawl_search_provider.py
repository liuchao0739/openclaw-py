"""Firecrawl provider module implements model/runtime integration."""

from __future__ import annotations

from typing import Any

from openclaw.agents.tools.common import read_positive_integer_param
from openclaw_extensions.firecrawl.web_search_shared import build_firecrawl_web_search_provider_base

GENERIC_FIRECRAWL_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query string."},
        "count": {
            "type": "integer",
            "description": "Number of results to return (1-10).",
            "minimum": 1,
            "maximum": 10,
        },
    },
    "additionalProperties": False,
}

_firecrawl_client_module: Any | None = None


async def _load_firecrawl_client_module() -> Any:
    global _firecrawl_client_module
    if _firecrawl_client_module is None:
        from openclaw_extensions.firecrawl.src import firecrawl_client

        _firecrawl_client_module = firecrawl_client
    return _firecrawl_client_module


def create_firecrawl_web_search_provider() -> dict[str, Any]:
    def create_tool(ctx: dict[str, Any]) -> dict[str, Any]:
        async def execute(args: dict[str, Any]) -> dict[str, Any]:
            client = await _load_firecrawl_client_module()
            return await client.run_firecrawl_search(
                {
                    "cfg": ctx.get("config"),
                    "query": args.get("query") if isinstance(args.get("query"), str) else "",
                    "count": read_positive_integer_param(
                        args,
                        "count",
                        message="count must be an integer from 1 to 10",
                        max_value=10,
                    ),
                }
            )

        return {
            "description": (
                "Search the web using Firecrawl. Returns structured results with snippets from "
                "Firecrawl Search. Use firecrawl_search for Firecrawl-specific knobs like sources "
                "or categories."
            ),
            "parameters": GENERIC_FIRECRAWL_SEARCH_SCHEMA,
            "execute": execute,
        }

    return {
        **build_firecrawl_web_search_provider_base(),
        "create_tool": create_tool,
    }
