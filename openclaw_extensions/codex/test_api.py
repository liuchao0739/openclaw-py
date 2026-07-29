from .src.app_server.config import resolve_codex_app_server_runtime_options


def resolve_codex_prompt_snapshot_app_server_options(plugin_config=None):
    return resolve_codex_app_server_runtime_options({
        "pluginConfig": plugin_config,
        "env": {},
        "requirementsToml": None,
    })


def build_codex_harness_prompt_snapshot(params: dict) -> dict:
    from .src.app_server.thread_lifecycle import (
        build_developer_instructions,
        build_thread_resume_params,
        build_thread_start_params,
        build_turn_start_params,
    )

    developer_instructions = _join_present_sections(
        build_developer_instructions(params["attempt"], {"dynamicTools": params["dynamicTools"]}),
        params.get("developerInstructionAdditions"),
    )
    return {
        "developerInstructions": developer_instructions,
        "threadStartParams": build_thread_start_params(params["attempt"], {
            "cwd": params["cwd"],
            "dynamicTools": params["dynamicTools"],
            "appServer": params["appServer"],
            "developerInstructions": developer_instructions,
            "config": params.get("config"),
        }),
        "threadResumeParams": build_thread_resume_params(params["attempt"], {
            "threadId": params["threadId"],
            "appServer": params["appServer"],
            "developerInstructions": developer_instructions,
            "config": params.get("config"),
        }),
        "turnStartParams": build_turn_start_params(params["attempt"], {
            "threadId": params["threadId"],
            "cwd": params["cwd"],
            "appServer": params["appServer"],
            "promptText": params.get("promptText"),
            "turnScopedDeveloperInstructions": params.get("turnScopedDeveloperInstructions"),
            "heartbeatCollaborationInstructions": params.get("heartbeatCollaborationInstructions"),
        }),
    }


def _join_present_sections(*sections) -> str:
    return "\n\n".join(
        section for section in sections
        if section and section.strip()
    )


def create_codex_dynamic_tool_specs_for_prompt_snapshot(params: dict) -> list:
    from .src.app_server.dynamic_tool_profile import filter_codex_dynamic_tools
    from .src.app_server.dynamic_tools import create_codex_dynamic_tool_bridge

    plugin_config = params.get("pluginConfig") or {}
    filtered_tools = filter_codex_dynamic_tools(params["tools"], plugin_config)
    return create_codex_dynamic_tool_bridge({
        "tools": filtered_tools,
        "signal": None,
        "loading": plugin_config.get("codexDynamicToolsLoading") or "searchable",
        "directToolNames": params.get("directToolNames"),
    })["specs"]
