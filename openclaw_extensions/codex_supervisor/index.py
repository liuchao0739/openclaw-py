"""Bundled plugin entry that exposes Codex app-server supervisor tools to OpenClaw agents."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.codex_supervisor.src.config import (
    codex_supervisor_plugin_config_schema,
    resolve_codex_supervisor_plugin_config,
)
from openclaw_extensions.codex_supervisor.src.plugin_tools import create_codex_supervisor_tools
from openclaw_extensions.codex_supervisor.src.supervisor import CodexSupervisor


def _register(api: OpenClawPluginApi) -> None:
    plugin_config = getattr(api, "plugin_config", None)
    config = resolve_codex_supervisor_plugin_config(plugin_config)
    supervisor = CodexSupervisor(config["endpoints"])
    api.lifecycle.register_runtime_lifecycle(  # type: ignore[attr-defined]
        {
            "id": "codex-supervisor",
            "description": "Close Codex supervisor app-server connections.",
            "cleanup": lambda **_ctx: supervisor.close(),
        }
    )
    for tool in create_codex_supervisor_tools(
        {
            "supervisor": supervisor,
            "policy": {
                "allowRawTranscripts": config["allowRawTranscripts"],
                "allowWriteControls": config["allowWriteControls"],
            },
        }
    ):
        api.register_tool(tool)  # type: ignore[attr-defined]


default = define_plugin_entry(
    id="codex-supervisor",
    name="Codex Supervisor",
    description="Supervise Codex app-server sessions from OpenClaw.",
    config_schema=codex_supervisor_plugin_config_schema,
    register=_register,
)
