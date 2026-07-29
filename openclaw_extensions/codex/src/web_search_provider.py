from openclaw.plugin_sdk.plugin_config_runtime import resolve_plugin_config_object

from .web_search_provider_shared import create_codex_web_search_provider_base

_codex_web_search_runtime = None


def _load_codex_web_search_runtime():
    global _codex_web_search_runtime
    if _codex_web_search_runtime is None:
        from . import web_search_provider_runtime as _codex_web_search_runtime
    return _codex_web_search_runtime


CODEX_WEB_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query. Include the desired region, time range, and constraints.",
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}


def create_codex_web_search_provider(options: dict = None) -> dict:
    options = options or {}
    base = create_codex_web_search_provider_base()

    def _create_tool(ctx):
        native_config = (ctx.get("searchConfig") or {}).get("openaiCodex")
        if (
            native_config
            and isinstance(native_config, dict)
            and not isinstance(native_config, list)
            and native_config.get("enabled") is False
        ):
            return None

        async def _execute(args, execution_context):
            runtime = _load_codex_web_search_runtime()
            plugin_config = (
                options["resolvePluginConfig"]()
                if options.get("resolvePluginConfig")
                else resolve_plugin_config_object(ctx.get("config"), "codex")
            )
            return await runtime.execute_codex_web_search_provider_tool(ctx, args, execution_context, {
                "pluginConfig": plugin_config,
                "clientFactory": options.get("clientFactory"),
            })

        return {
            "description": "Search the current web through Codex hosted search and return a grounded answer with source URLs.",
            "parameters": CODEX_WEB_SEARCH_SCHEMA,
            "execute": _execute,
        }

    base["createTool"] = _create_tool
    return base
