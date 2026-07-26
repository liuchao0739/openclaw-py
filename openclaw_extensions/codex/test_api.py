"""Test-only helpers for Codex app-server prompt snapshots and dynamic tool specs."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.codex.src.app_server.config import resolve_codex_app_server_runtime_options
from openclaw_extensions.codex.src.app_server.dynamic_tool_profile import filter_codex_dynamic_tools
from openclaw_extensions.codex.src.app_server.dynamic_tools import create_codex_dynamic_tool_bridge
from openclaw_extensions.codex.src.app_server.thread_lifecycle import (
    build_developer_instructions,
    build_thread_resume_params,
    build_thread_start_params,
    build_turn_start_params,
)


def resolve_codex_prompt_snapshot_app_server_options(plugin_config: Any = None) -> dict[str, Any]:
    return resolve_codex_app_server_runtime_options(
        {
            "pluginConfig": plugin_config,
            "env": {},
            "requirementsToml": None,
        }
    )


def _join_present_sections(*sections: Any) -> str:
    return "\n\n".join(
        section.strip()
        for section in sections
        if isinstance(section, str) and section.strip()
    )


def build_codex_harness_prompt_snapshot(params: dict[str, Any]) -> dict[str, Any]:
    attempt = params["attempt"]
    developer_instructions = _join_present_sections(
        build_developer_instructions(attempt, {"dynamicTools": params.get("dynamicTools")}),
        params.get("developerInstructionAdditions"),
    )
    return {
        "developerInstructions": developer_instructions,
        "threadStartParams": build_thread_start_params(
            attempt,
            {
                "cwd": params["cwd"],
                "dynamicTools": params.get("dynamicTools") or [],
                "appServer": params["appServer"],
                "developerInstructions": developer_instructions,
                "config": params.get("config"),
            },
        ),
        "threadResumeParams": build_thread_resume_params(
            attempt,
            {
                "threadId": params["threadId"],
                "appServer": params["appServer"],
                "developerInstructions": developer_instructions,
                "config": params.get("config"),
            },
        ),
        "turnStartParams": build_turn_start_params(
            attempt,
            {
                "threadId": params["threadId"],
                "cwd": params["cwd"],
                "appServer": params["appServer"],
                "promptText": params.get("promptText"),
                "turnScopedDeveloperInstructions": params.get("turnScopedDeveloperInstructions"),
                "heartbeatCollaborationInstructions": params.get("heartbeatCollaborationInstructions"),
            },
        ),
    }


def create_codex_dynamic_tool_specs_for_prompt_snapshot(params: dict[str, Any]) -> list[dict[str, Any]]:
    plugin_config = params.get("pluginConfig") or {}
    filtered_tools = filter_codex_dynamic_tools(params.get("tools") or [], plugin_config)
    bridge = create_codex_dynamic_tool_bridge(
        {
            "tools": filtered_tools,
            "signal": None,
            "loading": plugin_config.get("codexDynamicToolsLoading") or "searchable",
            "directToolNames": params.get("directToolNames"),
        }
    )
    return bridge["specs"]
