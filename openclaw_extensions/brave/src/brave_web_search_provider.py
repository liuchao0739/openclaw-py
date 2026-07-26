"""Brave web-search provider factory."""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw.plugin_sdk.provider_web_search import (
    merge_scoped_search_config,
    resolve_provider_web_search_plugin_config,
)
from openclaw_extensions.brave.src.brave_web_search_provider_shared import resolve_brave_mode
from openclaw_extensions.brave.web_search_shared import build_brave_web_search_provider_base

BRAVE_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query string."},
        "count": {
            "type": "integer",
            "description": "Number of results to return (1-10).",
            "minimum": 1,
            "maximum": 10,
        },
        "country": {
            "type": "string",
            "description": (
                "2-letter country code for region-specific results "
                "(e.g., 'DE', 'US', 'ALL'). Default: 'US'."
            ),
        },
        "language": {
            "type": "string",
            "description": "ISO 639-1 language code for results (e.g., 'en', 'de', 'fr').",
        },
        "freshness": {
            "type": "string",
            "description": "Filter by time: 'day' (24h), 'week', 'month', or 'year'.",
        },
        "date_after": {
            "type": "string",
            "description": "Only results published after this date (YYYY-MM-DD).",
        },
        "date_before": {
            "type": "string",
            "description": "Only results published before this date (YYYY-MM-DD).",
        },
        "search_lang": {
            "type": "string",
            "description": (
                "Brave language code for search results "
                "(e.g., 'en', 'de', 'en-gb', 'zh-hans', 'zh-hant', 'pt-br')."
            ),
        },
        "ui_lang": {
            "type": "string",
            "description": (
                "Locale code for UI elements in language-region format "
                "(e.g., 'en-US', 'de-DE', 'fr-FR', 'tr-TR'). Must include region subtag."
            ),
        },
    },
}

_brave_runtime_module: Any | None = None


def _is_diagnostic_flag_enabled(flag: str, config: dict[str, Any] | None = None) -> bool:
    if not config:
        return False
    diagnostics = config.get("diagnostics")
    if not is_record(diagnostics):
        return False
    flags = diagnostics.get("flags")
    if not isinstance(flags, list):
        return False
    target = flag.lower()
    for enabled in flags:
        if not isinstance(enabled, str):
            continue
        enabled_lower = enabled.lower()
        if enabled_lower in ("*", "all"):
            return True
        if enabled_lower == target:
            return True
        if enabled_lower.endswith(".*"):
            prefix = enabled_lower[:-2]
            if target == prefix or target.startswith(f"{prefix}."):
                return True
        if enabled_lower.endswith("*") and not enabled_lower.endswith(".*"):
            prefix = enabled_lower[:-1]
            if target.startswith(prefix):
                return True
    return False


def _resolve_brave_mode_from_search_config(search_config: dict[str, Any] | None = None) -> str:
    brave = search_config.get("brave") if search_config and is_record(search_config.get("brave")) else None
    return resolve_brave_mode(brave if isinstance(brave, dict) else None)


async def _load_brave_web_search_runtime():
    global _brave_runtime_module
    if _brave_runtime_module is None:
        from openclaw_extensions.brave.src import brave_web_search_provider_runtime

        _brave_runtime_module = brave_web_search_provider_runtime
    return _brave_runtime_module


def _merge_brave_search_config(
    search_config: dict[str, Any] | None,
    plugin_config: dict[str, Any] | None,
) -> dict[str, Any] | None:
    merged = merge_scoped_search_config(search_config, "brave", plugin_config)
    if not plugin_config:
        return merged
    result = dict(merged) if merged else {}
    if "apiKey" in plugin_config:
        result["apiKey"] = plugin_config["apiKey"]
    return result


def create_brave_web_search_provider() -> dict[str, Any]:
    def create_tool(ctx: dict[str, Any]) -> dict[str, Any]:
        search_config = _merge_brave_search_config(
            ctx.get("search_config") if is_record(ctx.get("search_config")) else None,
            resolve_provider_web_search_plugin_config(
                ctx.get("config") if is_record(ctx.get("config")) else None,
                "brave",
            ),
        )
        config = ctx.get("config") if is_record(ctx.get("config")) else None
        brave_mode = _resolve_brave_mode_from_search_config(search_config)
        diagnostics_enabled = _is_diagnostic_flag_enabled("brave.http", config)

        async def execute(args: dict[str, Any]) -> dict[str, Any]:
            runtime = await _load_brave_web_search_runtime()
            return await runtime.execute_brave_search(
                args,
                search_config,
                {"diagnostics_enabled": diagnostics_enabled},
            )

        description = (
            "Search the web using Brave Search LLM Context API. Returns pre-extracted page "
            "content (text chunks, tables, code blocks) optimized for LLM grounding."
            if brave_mode == "llm-context"
            else (
                "Search the web using Brave Search API. Supports region-specific and localized "
                "search via country and language parameters. Returns titles, URLs, and snippets "
                "for fast research."
            )
        )

        return {
            "description": description,
            "parameters": BRAVE_SEARCH_SCHEMA,
            "execute": execute,
        }

    return {
        **build_brave_web_search_provider_base(),
        "create_tool": create_tool,
    }
