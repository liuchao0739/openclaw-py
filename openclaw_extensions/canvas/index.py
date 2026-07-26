"""Canvas plugin entrypoint for node canvas control, hosted A2UI routes, and node CLI."""

from __future__ import annotations

import importlib
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry

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


def _tool_context_config(ctx: Any) -> Any:
    if isinstance(ctx, Mapping):
        return ctx.get("runtime_config") or ctx.get("config")
    runtime_config = getattr(ctx, "runtime_config", None)
    if runtime_config is not None:
        return runtime_config
    return getattr(ctx, "config", None)


def _tool_context_workspace_dir(ctx: Any) -> str | None:
    if isinstance(ctx, Mapping):
        value = ctx.get("workspace_dir")
        return str(value) if value is not None else None
    value = getattr(ctx, "workspace_dir", None)
    return str(value) if value is not None else None


def create_lazy_canvas_tool(
    *,
    config: Any | None = None,
    workspace_dir: str | None = None,
) -> Any:
    tool_schema_module = importlib.import_module("openclaw_extensions.canvas.src.tool_schema")
    loaded_tool: Any | None = None

    async def load_tool() -> Any:
        nonlocal loaded_tool
        if loaded_tool is None:
            tool_module = importlib.import_module("openclaw_extensions.canvas.src.tool")
            loaded_tool = tool_module.create_canvas_tool(
                config=config,
                workspace_dir=workspace_dir,
            )
        return loaded_tool

    async def execute(*args: Any) -> Any:
        tool = await load_tool()
        result = tool.execute(*args)
        if isinstance(result, Awaitable):
            return await result
        return result

    return {
        "label": "Canvas",
        "name": "canvas",
        "description": (
            "Control node canvases (present/hide/navigate/eval/snapshot/A2UI). "
            "Use snapshot to capture the rendered UI."
        ),
        "parameters": tool_schema_module.CanvasToolSchema,
        "execute": execute,
    }


def _register(api: OpenClawPluginApi) -> None:
    config_module = importlib.import_module("openclaw_extensions.canvas.src.config")
    a2ui_shared_module = importlib.import_module("openclaw_extensions.canvas.src.host.a2ui_shared")

    if config_module.is_canvas_host_enabled(api.config):  # type: ignore[attr-defined]
        http_route_handler: Any | None = None

        async def load_http_route_handler() -> Any:
            nonlocal http_route_handler
            if http_route_handler is None:
                http_route_module = importlib.import_module(
                    "openclaw_extensions.canvas.src.http_route"
                )
                http_route_handler = http_route_module.create_canvas_http_route_handler(
                    {
                        "config": api.config,
                        "plugin_config": getattr(api, "plugin_config", None),
                        "runtime": {
                            "log": lambda *args: api.logger.info(" ".join(str(arg) for arg in args)),
                            "error": lambda *args: api.logger.error(
                                " ".join(str(arg) for arg in args)
                            ),
                            "exit": lambda code: (_raise_canvas_host_exit(code)),
                        },
                    }
                )
            return http_route_handler

        async def handle_http_request(req: Any, res: Any) -> Any:
            handler = await load_http_route_handler()
            result = handler.handle_http_request(req, res)
            if isinstance(result, Awaitable):
                return await result
            return result

        async def handle_upgrade(req: Any, socket: Any, head: bytes) -> Any:
            handler = await load_http_route_handler()
            result = handler.handle_upgrade(req, socket, head)
            if isinstance(result, Awaitable):
                return await result
            return result

        node_capability = {"surface": "canvas"}
        api.register_http_route(
            {
                "path": a2ui_shared_module.A2UI_PATH,
                "auth": "plugin",
                "match": "prefix",
                "nodeCapability": node_capability,
                "handler": handle_http_request,
            }
        )
        api.register_http_route(
            {
                "path": a2ui_shared_module.CANVAS_HOST_PATH,
                "auth": "plugin",
                "match": "prefix",
                "nodeCapability": node_capability,
                "handler": handle_http_request,
            }
        )
        api.register_http_route(
            {
                "path": a2ui_shared_module.CANVAS_WS_PATH,
                "auth": "plugin",
                "match": "exact",
                "nodeCapability": node_capability,
                "handler": handle_http_request,
                "handleUpgrade": handle_upgrade,
            }
        )

        class CanvasHostService:
            id = "canvas-host"

            def start(self, _ctx: Any) -> None:
                return None

            async def stop(self, _ctx: Any) -> None:
                handler = http_route_handler
                if handler is not None:
                    close = handler.close()
                    if isinstance(close, Awaitable):
                        await close

        api.register_service(CanvasHostService())  # type: ignore[arg-type]

        resolve_canvas_http_path_to_local_path: Callable[[str], Any] | None = None

        async def resolve_hosted_media(media_url: str) -> Any:
            nonlocal resolve_canvas_http_path_to_local_path
            if resolve_canvas_http_path_to_local_path is None:
                documents_module = importlib.import_module(
                    "openclaw_extensions.canvas.src.documents"
                )
                resolve_canvas_http_path_to_local_path = (
                    documents_module.resolve_canvas_http_path_to_local_path
                )
            return resolve_canvas_http_path_to_local_path(media_url)

        api.register_hosted_media_resolver(resolve_hosted_media)  # type: ignore[attr-defined]

    api.register_node_invoke_policy(  # type: ignore[attr-defined]
        {
            "commands": CANVAS_NODE_COMMANDS,
            "defaultPlatforms": ["ios", "android", "macos", "windows", "unknown"],
            "foregroundRestrictedOnIos": True,
            "handle": lambda ctx: ctx.invoke_node(),
        }
    )
    api.register_tool(  # type: ignore[attr-defined]
        lambda ctx: create_lazy_canvas_tool(
            config=_tool_context_config(ctx),
            workspace_dir=_tool_context_workspace_dir(ctx),
        )
    )

    async def register_canvas_cli(ctx: Any) -> None:
        cli_module = importlib.import_module("openclaw_extensions.canvas.src.cli")
        cli_module.register_nodes_canvas_commands(
            ctx["program"] if isinstance(ctx, Mapping) else ctx.program,
            cli_module.create_default_canvas_cli_dependencies(),
        )

    api.register_node_cli_feature(  # type: ignore[attr-defined]
        register_canvas_cli,
        {
            "descriptors": [
                {
                    "name": "canvas",
                    "description": "Capture or render canvas content from a paired node",
                    "hasSubcommands": True,
                },
            ],
        },
    )


def _raise_canvas_host_exit(code: Any) -> None:
    raise RuntimeError(f"canvas host requested process exit {code}")


def _canvas_config_schema() -> Any:
    config_module = importlib.import_module("openclaw_extensions.canvas.src.config")
    return config_module.canvas_config_schema


default = define_plugin_entry(
    id="canvas",
    name="Canvas",
    description="Experimental Canvas control and A2UI rendering surfaces for paired nodes.",
    config_schema=_canvas_config_schema,
    reload={
        "restartPrefixes": [
            "plugins.enabled",
            "plugins.allow",
            "plugins.deny",
            "plugins.entries.canvas",
        ],
    },
    register=_register,
)
