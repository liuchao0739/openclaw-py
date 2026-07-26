"""Codex app-server agent harness registration and lazy runtime boundaries."""

from __future__ import annotations

import importlib
from typing import Any

DEFAULT_CODEX_HARNESS_PROVIDER_IDS = frozenset({"codex", "openai"})
CODEX_APP_SERVER_CONTEXT_ENGINE_HOST_CAPABILITIES = (
    "bootstrap",
    "assemble-before-prompt",
    "after-turn",
    "maintain",
    "compact",
    "runtime-llm-complete",
    "thread-bootstrap-projection",
)


def create_codex_app_server_agent_harness(options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create the Codex app-server harness used for attempts, side questions, and compaction."""
    options = options or {}
    provider_ids = {
        str(provider_id).strip().lower()
        for provider_id in (options.get("providerIds") or DEFAULT_CODEX_HARNESS_PROVIDER_IDS)
    }

    def _resolve_plugin_config() -> Any:
        resolver = options.get("resolvePluginConfig")
        if callable(resolver):
            return resolver()
        return options.get("pluginConfig")

    def supports(ctx: dict[str, Any]) -> dict[str, Any]:
        provider = str(ctx.get("provider") or "").strip().lower()
        if provider in provider_ids:
            return {"supported": True, "priority": 100}
        ordered = ", ".join(sorted(provider_ids))
        return {"supported": False, "reason": f"provider is not one of: {ordered}"}

    async def run_attempt(params: dict[str, Any]) -> Any:
        module = importlib.import_module("openclaw_extensions.codex.src.app_server.run_attempt")
        return await module.run_codex_app_server_attempt(
            params,
            {
                "pluginConfig": _resolve_plugin_config(),
                "nativeHookRelay": {"enabled": True},
            },
        )

    async def run_side_question(params: dict[str, Any]) -> Any:
        module = importlib.import_module("openclaw_extensions.codex.src.app_server.side_question")
        return await module.run_codex_app_server_side_question(
            params,
            {
                "pluginConfig": _resolve_plugin_config(),
                "nativeHookRelay": {"enabled": True},
            },
        )

    async def compact(params: dict[str, Any]) -> Any:
        module = importlib.import_module("openclaw_extensions.codex.src.app_server.compact")
        return await module.maybe_compact_codex_app_server_session(
            params,
            {"pluginConfig": _resolve_plugin_config()},
        )

    async def compact_after_context_engine(params: dict[str, Any]) -> Any:
        module = importlib.import_module("openclaw_extensions.codex.src.app_server.compact")
        return await module.maybe_compact_codex_app_server_session(
            params,
            {
                "pluginConfig": _resolve_plugin_config(),
                "allowNonManualNativeRequest": True,
            },
        )

    async def reset(params: dict[str, Any]) -> None:
        session_file = params.get("sessionFile")
        if session_file:
            module = importlib.import_module("openclaw_extensions.codex.src.app_server.session_binding")
            await module.clear_codex_app_server_binding(session_file)

    async def dispose() -> None:
        module = importlib.import_module("openclaw_extensions.codex.src.app_server.shared_client")
        await module.clear_shared_codex_app_server_client_and_wait()

    return {
        "id": options.get("id") or "codex",
        "label": options.get("label") or "Codex agent harness",
        "contextEngineHostCapabilities": list(CODEX_APP_SERVER_CONTEXT_ENGINE_HOST_CAPABILITIES),
        "deliveryDefaults": {"sourceVisibleReplies": "message_tool"},
        "supports": supports,
        "runAttempt": run_attempt,
        "runSideQuestion": run_side_question,
        "compact": compact,
        "compactAfterContextEngine": compact_after_context_engine,
        "reset": reset,
        "dispose": dispose,
    }
