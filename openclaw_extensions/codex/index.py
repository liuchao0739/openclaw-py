from openclaw.plugin_sdk.config_contracts import OpenClawConfig
from openclaw.plugin_sdk.config_mutation import mutate_config_file
from openclaw.plugin_sdk.plugin_config_runtime import resolve_live_plugin_config_object
from openclaw.plugin_sdk.plugin_entry import define_plugin_entry

from .harness import create_codex_app_server_agent_harness
from .media_understanding_provider import build_codex_media_understanding_provider
from .provider import build_codex_provider
from .src.commands import create_codex_command
from .src.conversation_binding import (
    handle_codex_conversation_binding_resolved,
    handle_codex_conversation_inbound_claim,
)
from .src.migration.provider import build_codex_migration_provider
from .src.node_cli_sessions import (
    create_codex_cli_session_node_host_commands,
    create_codex_cli_session_node_invoke_policies,
    list_codex_cli_sessions_on_node,
    resume_codex_cli_session_on_node,
    resolve_codex_cli_session_for_binding_on_node,
)
from .src.web_search_provider import create_codex_web_search_provider


def _build_entry():
    def _register(api):
        def _resolve_current_config():
            if api["runtime"].get("config", {}).get("current"):
                return api["runtime"]["config"]["current"]()
            return None

        def _resolve_current_plugin_config():
            resolved = resolve_live_plugin_config_object(
                _resolve_current_config,
                "codex",
                api.get("pluginConfig"),
            )
            return resolved if resolved is not None else api.get("pluginConfig")

        api.register_agent_harness(
            create_codex_app_server_agent_harness({"resolvePluginConfig": _resolve_current_plugin_config})
        )
        api.register_provider(build_codex_provider({"pluginConfig": api.get("pluginConfig")}))
        api.register_media_understanding_provider(
            build_codex_media_understanding_provider({"pluginConfig": api.get("pluginConfig")})
        )
        api.register_web_search_provider(
            create_codex_web_search_provider({"resolvePluginConfig": _resolve_current_plugin_config})
        )
        api.register_migration_provider(build_codex_migration_provider({"runtime": api.get("runtime")}))
        for command in create_codex_cli_session_node_host_commands():
            api.register_node_host_command(command)
        for policy in create_codex_cli_session_node_invoke_policies():
            api.register_node_invoke_policy(policy)

        def _read_codex_plugins_config():
            current = (api["runtime"].get("config", {}).get("current", lambda: {})() or {}) if api.get("runtime") else {}
            plugins = current.get("plugins") if isinstance(current, dict) else None
            if not plugins or not isinstance(plugins, dict):
                return {}
            entries = plugins.get("entries")
            if not entries or not isinstance(entries, dict):
                return {}
            codex_entry = entries.get("codex")
            if not codex_entry or not isinstance(codex_entry, dict):
                return {}
            config = codex_entry.get("config")
            if not config or not isinstance(config, dict):
                return {}
            codex_plugins = config.get("codexPlugins")
            if not codex_plugins or not isinstance(codex_plugins, dict):
                return {}
            declared = codex_plugins.get("plugins")
            if not declared or not isinstance(declared, dict):
                return {"enabled": codex_plugins.get("enabled") is True}
            return {"enabled": codex_plugins.get("enabled") is True, "plugins": declared}

        async def _mutate_codex_plugins_config(update):
            def _mutate(draft):
                root = draft
                root["plugins"] = root.get("plugins") or {}
                plugins_block = root["plugins"]
                plugins_block["entries"] = plugins_block.get("entries") or {}
                entries = plugins_block["entries"]
                entries["codex"] = entries.get("codex") or {}
                codex_entry = entries["codex"]
                codex_entry["config"] = codex_entry.get("config") or {}
                config = codex_entry["config"]
                config["codexPlugins"] = config.get("codexPlugins") or {}
                codex_plugins = config["codexPlugins"]
                codex_plugins["plugins"] = codex_plugins.get("plugins") or {}
                update(codex_plugins)

            await mutate_config_file({"mutate": _mutate})

        api.register_command(
            create_codex_command({
                "pluginConfig": api.get("pluginConfig"),
                "deps": {
                    "listCodexCliSessionsOnNode": lambda params: list_codex_cli_sessions_on_node({"runtime": api["runtime"], **params}),
                    "resolveCodexCliSessionForBindingOnNode": lambda params: resolve_codex_cli_session_for_binding_on_node({"runtime": api["runtime"], **params}),
                    "codexPluginsManagementIo": {
                        "read": _read_codex_plugins_config,
                        "mutate": _mutate_codex_plugins_config,
                    },
                },
            })
        )

        def _inbound_claim(event, ctx):
            return handle_codex_conversation_inbound_claim(event, ctx, {
                "pluginConfig": _resolve_current_plugin_config(),
                "config": _resolve_current_config(),
                "resumeCodexCliSessionOnNode": lambda params: resume_codex_cli_session_on_node({"runtime": api["runtime"], **params}),
            })

        api.on("inbound_claim", _inbound_claim)
        if api.get("onConversationBindingResolved"):
            api["onConversationBindingResolved"](handle_codex_conversation_binding_resolved)

    return define_plugin_entry({
        "id": "codex",
        "name": "Codex",
        "description": "Codex app-server harness and Codex-managed GPT model catalog.",
        "register": _register,
    })


plugin_entry = _build_entry()
