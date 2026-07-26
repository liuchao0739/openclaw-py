"""Codex hosted web search provider."""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw_extensions.codex.src.web_search_provider_runtime import (
    execute_codex_web_search_provider_tool,
)
from openclaw_extensions.codex.src.web_search_provider_shared import (
    create_codex_web_search_provider_base,
)

CODEX_WEB_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query. Include the desired region, time range, and constraints.",
        }
    },
    "required": ["query"],
    "additionalProperties": False,
}


def _resolve_plugin_config_object(config: dict[str, Any] | None, plugin_id: str) -> dict[str, Any] | None:
    if not is_record(config):
        return None
    plugins = config.get("plugins")
    if not is_record(plugins):
        return None
    entries = plugins.get("entries")
    if not is_record(entries):
        return None
    entry = entries.get(plugin_id)
    if not is_record(entry):
        return None
    plugin_config = entry.get("config")
    return plugin_config if is_record(plugin_config) else None


def create_codex_web_search_provider(options: dict[str, Any] | None = None) -> dict[str, Any]:
    options = options or {}

    def create_tool(ctx: dict[str, Any]) -> dict[str, Any] | None:
        native_config = (ctx.get("searchConfig") or {}).get("openaiCodex")
        if (
            is_record(native_config)
            and native_config.get("enabled") is False
        ):
            return None

        async def execute(args: dict[str, Any], execution_context: dict[str, Any]) -> Any:
            plugin_config = options.get("resolvePluginConfig")
            resolved_plugin_config = (
                plugin_config()
                if callable(plugin_config)
                else _resolve_plugin_config_object(ctx.get("config"), "codex")
            )
            return await execute_codex_web_search_provider_tool(
                ctx,
                args,
                execution_context,
                {
                    "pluginConfig": resolved_plugin_config,
                    "clientFactory": options.get("clientFactory"),
                },
            )

        return {
            "description": (
                "Search the current web through Codex hosted search and return a grounded answer "
                "with source URLs."
            ),
            "parameters": CODEX_WEB_SEARCH_SCHEMA,
            "execute": execute,
        }

    return {
        **create_codex_web_search_provider_base(),
        "createTool": create_tool,
    }
