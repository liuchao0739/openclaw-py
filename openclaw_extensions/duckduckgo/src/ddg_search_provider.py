"""DuckDuckGo provider module implements model/runtime integration."""

from __future__ import annotations

from typing import Any

from openclaw.agents.tools.common import (
    read_positive_integer_param,
    read_string_param,
)
from openclaw_extensions.duckduckgo.src.ddg_search_provider_shared import (
    create_duck_duck_go_web_search_provider_base,
)

_DUCK_DUCK_GO_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query string."},
        "count": {
            "type": "integer",
            "description": "Number of results to return (1-10).",
            "minimum": 1,
            "maximum": 10,
        },
        "region": {
            "type": "string",
            "description": "Optional DuckDuckGo region code such as us-en, uk-en, or de-de.",
        },
        "safeSearch": {
            "type": "string",
            "description": "SafeSearch level: strict, moderate, or off.",
        },
    },
    "additionalProperties": False,
}

_ddg_client_module: Any | None = None


async def _load_ddg_client_module():
    global _ddg_client_module
    if _ddg_client_module is None:
        from openclaw_extensions.duckduckgo.src import ddg_client

        _ddg_client_module = ddg_client
    return _ddg_client_module


def create_duck_duck_go_web_search_provider() -> dict[str, Any]:
    def create_tool(ctx: dict[str, Any]) -> dict[str, Any]:
        async def execute(args: dict[str, Any]) -> dict[str, Any]:
            ddg_client = await _load_ddg_client_module()
            safe_search = read_string_param(args, "safeSearch")
            if safe_search not in ("strict", "moderate", "off"):
                safe_search = read_string_param(args, "safe_search")
            return await ddg_client.run_duck_duck_go_search(
                {
                    "config": ctx.get("config"),
                    "query": read_string_param(args, "query", required=True),
                    "count": read_positive_integer_param(
                        args,
                        "count",
                        max_value=10,
                        message="count must be an integer from 1 to 10.",
                    ),
                    "region": read_string_param(args, "region"),
                    "safeSearch": safe_search,
                }
            )

        return {
            "description": (
                "Search the web using DuckDuckGo. Returns titles, URLs, and snippets "
                "with no API key required."
            ),
            "parameters": _DUCK_DUCK_GO_SEARCH_SCHEMA,
            "execute": execute,
        }

    return {
        **create_duck_duck_go_web_search_provider_base(),
        "create_tool": create_tool,
    }
