from typing import Any, Optional

from .config import canvas_config_schema, is_canvas_host_enabled
from .host.a2ui_shared import A2UI_PATH, CANVAS_HOST_PATH, CANVAS_WS_PATH
from .tool_schema import CanvasToolSchema
from .tool import create_canvas_tool

CANVAS_NODE_COMMANDS = [
    "canvas.present",
    "canvas.hide",
    "canvas.navigate",
    "canvas.eval",
    "canvas.snapshot",
    "canvas.a2ui.push",
    "canvas.a2ui.pushJSONL",
    "canvas.a2ui.reset",
]


def _create_lazy_canvas_tool(config: Any = None, workspace_dir: Optional[str] = None) -> dict:
    tool = None

    async def load_tool():
        nonlocal tool
        if tool is None:
            tool = create_canvas_tool(config=config, workspace_dir=workspace_dir)
        return tool

    async def execute(*args, **kwargs):
        loaded = await load_tool()
        return await loaded["execute"](*args, **kwargs)

    return {
        "label": "Canvas",
        "name": "canvas",
        "description": "Control node canvases (present/hide/navigate/eval/snapshot/A2UI). Use snapshot to capture the rendered UI.",
        "parameters": CanvasToolSchema,
        "execute": execute,
    }


plugin_entry: dict = {
    "id": "canvas",
    "name": "Canvas",
    "description": "Experimental Canvas control and A2UI rendering surfaces for paired nodes.",
    "configSchema": canvas_config_schema,
    "reload": {
        "restartPrefixes": [
            "plugins.enabled",
            "plugins.allow",
            "plugins.deny",
            "plugins.entries.canvas",
        ],
    },
    "register": {
        "nodeInvokePolicy": {
            "commands": CANVAS_NODE_COMMANDS,
            "defaultPlatforms": ["ios", "android", "macos", "windows", "unknown"],
            "foregroundRestrictedOnIos": True,
            "handle": lambda ctx: ctx.invoke_node(),
        },
        "tool": lambda ctx: _create_lazy_canvas_tool(
            config=ctx.get("runtimeConfig") or ctx.get("config"),
            workspace_dir=ctx.get("workspaceDir"),
        ),
        "nodeCliFeature": {
            "descriptors": [
                {
                    "name": "canvas",
                    "description": "Capture or render canvas content from a paired node",
                    "hasSubcommands": True,
                },
            ],
        },
        "hostRoutes": {
            "routes": [
                {"path": A2UI_PATH, "auth": "plugin", "match": "prefix", "nodeCapability": {"surface": "canvas"}},
                {"path": CANVAS_HOST_PATH, "auth": "plugin", "match": "prefix", "nodeCapability": {"surface": "canvas"}},
                {"path": CANVAS_WS_PATH, "auth": "plugin", "match": "exact", "nodeCapability": {"surface": "canvas"}},
            ],
            "enabled": lambda config: is_canvas_host_enabled(config),
        },
    },
}
