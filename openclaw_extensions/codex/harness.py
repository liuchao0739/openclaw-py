from typing import Iterable, Optional, Set

DEFAULT_CODEX_HARNESS_PROVIDER_IDS = {"codex", "openai"}
CODEX_APP_SERVER_CONTEXT_ENGINE_HOST_CAPABILITIES = [
    "bootstrap",
    "assemble-before-prompt",
    "after-turn",
    "maintain",
    "compact",
    "runtime-llm-complete",
    "thread-bootstrap-projection",
]


def create_codex_app_server_agent_harness(options: Optional[dict] = None) -> dict:
    options = options or {}
    provider_ids: Set[str] = {
        provider_id.strip().lower()
        for provider_id in (options.get("providerIds") or DEFAULT_CODEX_HARNESS_PROVIDER_IDS)
    }

    def _supports(ctx):
        provider = ctx["provider"].strip().lower()
        if provider in provider_ids:
            return {"supported": True, "priority": 100}
        return {
            "supported": False,
            "reason": f"provider is not one of: {', '.join(sorted(provider_ids))}",
        }

    async def _run_attempt(params):
        from .src.app_server.run_attempt import run_codex_app_server_attempt

        plugin_config = options.get("resolvePluginConfig")() if options.get("resolvePluginConfig") else options.get("pluginConfig")
        return await run_codex_app_server_attempt(params, {
            "pluginConfig": plugin_config,
            "nativeHookRelay": {"enabled": True},
        })

    async def _run_side_question(params):
        from .src.app_server.side_question import run_codex_app_server_side_question

        plugin_config = options.get("resolvePluginConfig")() if options.get("resolvePluginConfig") else options.get("pluginConfig")
        return await run_codex_app_server_side_question(params, {
            "pluginConfig": plugin_config,
            "nativeHookRelay": {"enabled": True},
        })

    async def _compact(params):
        from .src.app_server.compact import maybe_compact_codex_app_server_session

        plugin_config = options.get("resolvePluginConfig")() if options.get("resolvePluginConfig") else options.get("pluginConfig")
        return await maybe_compact_codex_app_server_session(params, {"pluginConfig": plugin_config})

    async def _compact_after_context_engine(params):
        from .src.app_server.compact import maybe_compact_codex_app_server_session

        plugin_config = options.get("resolvePluginConfig")() if options.get("resolvePluginConfig") else options.get("pluginConfig")
        return await maybe_compact_codex_app_server_session(params, {
            "pluginConfig": plugin_config,
            "allowNonManualNativeRequest": True,
        })

    async def _reset(params):
        if params.get("sessionFile"):
            from .src.app_server.session_binding import clear_codex_app_server_binding

            await clear_codex_app_server_binding(params["sessionFile"])

    async def _dispose():
        from .src.app_server.shared_client import clear_shared_codex_app_server_client_and_wait

        await clear_shared_codex_app_server_client_and_wait()

    harness = {
        "id": options.get("id") or "codex",
        "label": options.get("label") or "Codex agent harness",
        "contextEngineHostCapabilities": CODEX_APP_SERVER_CONTEXT_ENGINE_HOST_CAPABILITIES,
        "deliveryDefaults": {"sourceVisibleReplies": "message_tool"},
        "supports": _supports,
        "runAttempt": _run_attempt,
        "runSideQuestion": _run_side_question,
        "compact": _compact,
        "compactAfterContextEngine": _compact_after_context_engine,
        "reset": _reset,
        "dispose": _dispose,
    }
    return harness
