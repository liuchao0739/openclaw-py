from typing import Any, TypedDict

from .bitable import register_feishu_bitable_tools
from .channel import feishu_plugin
from .chat import register_feishu_chat_tools
from .docx import register_feishu_app_scopes_tool, register_feishu_doc_tools
from .drive import register_feishu_drive_tools
from .manifest import MANIFEST
from .perm import register_feishu_perm_tools
from .setup_core import feishu_setup_adapter
from .setup_surface import feishu_setup_wizard, run_feishu_login
from .subagent_hooks import (
    handle_feishu_subagent_delivery_target,
    handle_feishu_subagent_ended,
    handle_feishu_subagent_spawning,
)
from .thread_bindings import (
    create_feishu_thread_binding_manager,
    get_feishu_thread_binding_manager,
)
from .wiki import register_feishu_wiki_tools

PLUGIN_ID = MANIFEST["id"]
PLUGIN_NAME = MANIFEST["name"]
PLUGIN_DESCRIPTION = MANIFEST["description"]

feishu_session_binding_adapter_channels = ["feishu"]


class PluginEntry(TypedDict, total=False):
    id: str
    name: str
    description: str
    plugin: dict
    secrets: dict
    runtime: dict
    registerFull: Any


def _register_feishu_subagent_hooks(api: Any) -> None:
    if hasattr(api, "registerSubagentHooks"):
        api.registerSubagentHooks({
            "onSpawning": handle_feishu_subagent_spawning,
            "onDeliveryTarget": handle_feishu_subagent_delivery_target,
            "onEnded": handle_feishu_subagent_ended,
        })


def _register_full(api: Any) -> None:
    _register_feishu_subagent_hooks(api)
    register_feishu_doc_tools(api)
    register_feishu_chat_tools(api)
    register_feishu_wiki_tools(api)
    register_feishu_drive_tools(api)
    register_feishu_perm_tools(api)
    register_feishu_bitable_tools(api)
    register_feishu_app_scopes_tool(api)


plugin_entry: PluginEntry = {
    "id": PLUGIN_ID,
    "name": PLUGIN_NAME,
    "description": PLUGIN_DESCRIPTION,
    "plugin": {
        "exportName": "feishuPlugin",
        "value": feishu_plugin,
    },
    "secrets": {
        "exportName": "channelSecrets",
    },
    "runtime": {
        "exportName": "setFeishuRuntime",
    },
    "registerFull": _register_full,
}
