"""Bundled Codex plugin entry."""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.codex.harness import create_codex_app_server_agent_harness
from openclaw_extensions.codex.media_understanding_provider import (
    build_codex_media_understanding_provider,
)
from openclaw_extensions.codex.provider import build_codex_provider
from openclaw_extensions.codex.src.commands import create_codex_command
from openclaw_extensions.codex.src.conversation_binding import (
    handle_codex_conversation_binding_resolved,
    handle_codex_conversation_inbound_claim,
)
from openclaw_extensions.codex.src.migration.provider import build_codex_migration_provider
from openclaw_extensions.codex.src.node_cli_sessions import (
    create_codex_cli_session_node_host_commands,
    create_codex_cli_session_node_invoke_policies,
)
from openclaw_extensions.codex.src.web_search_provider import create_codex_web_search_provider


def _resolve_live_plugin_config_object(
    resolve_current_config: Any,
    plugin_id: str,
    fallback: Any,
) -> Any:
    config = resolve_current_config() if callable(resolve_current_config) else None
    if not is_record(config):
        return fallback
    plugins = config.get("plugins")
    if not is_record(plugins):
        return fallback
    entries = plugins.get("entries")
    if not is_record(entries):
        return fallback
    entry = entries.get(plugin_id)
    if not is_record(entry):
        return fallback
    plugin_config = entry.get("config")
    return plugin_config if plugin_config is not None else fallback


def _register(api: OpenClawPluginApi) -> None:
    def resolve_current_config() -> Any:
        runtime = getattr(api, "runtime", None)
        config_api = getattr(runtime, "config", None) if runtime is not None else None
        current = getattr(config_api, "current", None) if config_api is not None else None
        return current() if callable(current) else None

    def resolve_current_plugin_config() -> Any:
        return _resolve_live_plugin_config_object(
            resolve_current_config,
            "codex",
            api.plugin_config,
        )

    api.register_agent_harness(
        create_codex_app_server_agent_harness({"resolvePluginConfig": resolve_current_plugin_config})
    )
    api.register_provider(build_codex_provider({"pluginConfig": api.plugin_config}))
    api.register_media_understanding_provider(
        build_codex_media_understanding_provider({"pluginConfig": api.plugin_config})
    )
    api.register_web_search_provider(
        create_codex_web_search_provider({"resolvePluginConfig": resolve_current_plugin_config})
    )
    api.register_migration_provider(build_codex_migration_provider({"runtime": getattr(api, "runtime", None)}))
    for command in create_codex_cli_session_node_host_commands():
        api.register_node_host_command(command)
    for policy in create_codex_cli_session_node_invoke_policies():
        api.register_node_invoke_policy(policy)
    api.register_command(create_codex_command({"pluginConfig": api.plugin_config}))

    def on_inbound_claim(event: Any, ctx: Any) -> Any:
        return handle_codex_conversation_inbound_claim(
            event,
            ctx,
            {
                "pluginConfig": resolve_current_plugin_config(),
                "config": resolve_current_config(),
            },
        )

    api.on("inbound_claim", on_inbound_claim)
    on_binding_resolved = getattr(api, "on_conversation_binding_resolved", None) or getattr(
        api, "onConversationBindingResolved", None
    )
    if callable(on_binding_resolved):
        on_binding_resolved(handle_codex_conversation_binding_resolved)


default = define_plugin_entry(
    id="codex",
    name="Codex",
    description="Codex app-server harness and Codex-managed GPT model catalog.",
    register=_register,
)
