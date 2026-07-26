"""Tests for the canvas extension plugin entry."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


def _build_canvas_src_modules(mocks: SimpleNamespace) -> dict[str, ModuleType]:
    config_module = ModuleType("openclaw_extensions.canvas.src.config")
    config_module.canvas_config_schema = {"parse": lambda value: value or {}, "uiHints": {}}
    config_module.is_canvas_host_enabled = lambda _config: True

    a2ui_shared_module = ModuleType("openclaw_extensions.canvas.src.host.a2ui_shared")
    a2ui_shared_module.A2UI_PATH = "/__openclaw__/a2ui"
    a2ui_shared_module.CANVAS_HOST_PATH = "/__openclaw__/canvas"
    a2ui_shared_module.CANVAS_WS_PATH = "/__openclaw__/ws"

    tool_schema_module = ModuleType("openclaw_extensions.canvas.src.tool_schema")
    tool_schema_module.CanvasToolSchema = {}

    http_route_module = ModuleType("openclaw_extensions.canvas.src.http_route")
    http_route_module.create_canvas_http_route_handler = mocks.create_canvas_http_route_handler

    documents_module = ModuleType("openclaw_extensions.canvas.src.documents")
    documents_module.resolve_canvas_http_path_to_local_path = (
        mocks.resolve_canvas_http_path_to_local_path
    )

    cli_module = ModuleType("openclaw_extensions.canvas.src.cli")
    cli_module.create_default_canvas_cli_dependencies = mocks.create_default_canvas_cli_dependencies
    cli_module.register_nodes_canvas_commands = mocks.register_nodes_canvas_commands

    tool_module = ModuleType("openclaw_extensions.canvas.src.tool")
    tool_module.create_canvas_tool = mocks.create_canvas_tool

    return {
        "openclaw_extensions.canvas.src.config": config_module,
        "openclaw_extensions.canvas.src.host.a2ui_shared": a2ui_shared_module,
        "openclaw_extensions.canvas.src.tool_schema": tool_schema_module,
        "openclaw_extensions.canvas.src.http_route": http_route_module,
        "openclaw_extensions.canvas.src.documents": documents_module,
        "openclaw_extensions.canvas.src.cli": cli_module,
        "openclaw_extensions.canvas.src.tool": tool_module,
    }


def _install_canvas_src_mocks(mocks: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    src_modules = _build_canvas_src_modules(mocks)
    original_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None) -> ModuleType:
        if name in src_modules:
            return src_modules[name]
        return original_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    for module_name, module in src_modules.items():
        monkeypatch.setitem(sys.modules, module_name, module)


def _register_canvas(mocks: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    routes: list[dict[str, Any]] = []
    services: list[Any] = []
    resolvers: list[Any] = []
    tools: list[Any] = []
    cli_features: list[dict[str, Any]] = []

    class FakeApi:
        def __init__(self) -> None:
            self.config: dict[str, Any] = {}
            self.logger = SimpleNamespace(
                info=MagicMock(),
                warn=MagicMock(),
                error=MagicMock(),
                debug=MagicMock(),
            )

        def register_http_route(self, route: dict[str, Any]) -> None:
            routes.append(route)

        def register_service(self, service: Any) -> None:
            services.append(service)

        def register_hosted_media_resolver(self, resolver: Any) -> None:
            resolvers.append(resolver)

        def register_tool(self, tool: Any) -> None:
            tools.append(tool)

        def register_node_cli_feature(self, registrar: Any, opts: dict[str, Any]) -> None:
            cli_features.append({"registrar": registrar, "opts": opts})

        def register_node_invoke_policy(self, _policy: dict[str, Any]) -> None:
            return None

    _install_canvas_src_mocks(mocks, monkeypatch)

    from openclaw_extensions.canvas import index as canvas_index

    importlib.reload(canvas_index)
    canvas_index.default.register(FakeApi())

    return {
        "routes": routes,
        "services": services,
        "resolvers": resolvers,
        "tools": tools,
        "cli_features": cli_features,
    }


@pytest.fixture
def canvas_mocks() -> SimpleNamespace:
    http_handler = SimpleNamespace(
        handle_http_request=AsyncMock(return_value=True),
        handle_upgrade=AsyncMock(return_value=True),
        close=AsyncMock(return_value=None),
    )
    tool_execute = AsyncMock(return_value={"content": [{"type": "text", "text": "ok"}]})
    return SimpleNamespace(
        http_handler=http_handler,
        create_canvas_http_route_handler=MagicMock(return_value=http_handler),
        resolve_canvas_http_path_to_local_path=MagicMock(return_value="/tmp/canvas-asset"),
        create_default_canvas_cli_dependencies=MagicMock(return_value={"deps": True}),
        register_nodes_canvas_commands=MagicMock(),
        tool_execute=tool_execute,
        create_canvas_tool=MagicMock(
            return_value=SimpleNamespace(
                label="Canvas",
                name="canvas",
                description="Canvas",
                parameters={},
                execute=tool_execute,
            )
        ),
    )


@pytest.mark.asyncio
async def test_defers_canvas_host_implementation_until_registered_route_is_used(
    canvas_mocks: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registration = _register_canvas(canvas_mocks, monkeypatch)

    assert len(registration["routes"]) == 3
    assert len(registration["services"]) == 1
    canvas_mocks.create_canvas_http_route_handler.assert_not_called()

    await registration["services"][0].stop({})
    canvas_mocks.create_canvas_http_route_handler.assert_not_called()

    await registration["routes"][0]["handler"](
        SimpleNamespace(url="/__openclaw__/canvas"),
        {},
    )
    canvas_mocks.create_canvas_http_route_handler.assert_called_once()
    canvas_mocks.http_handler.handle_http_request.assert_called_once()

    await registration["services"][0].stop({})
    canvas_mocks.http_handler.close.assert_called_once()


@pytest.mark.asyncio
async def test_defers_canvas_resolver_cli_and_tool_implementations_until_use(
    canvas_mocks: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registration = _register_canvas(canvas_mocks, monkeypatch)

    assert len(registration["resolvers"]) == 1
    assert len(registration["tools"]) == 1
    assert len(registration["cli_features"]) == 1
    canvas_mocks.resolve_canvas_http_path_to_local_path.assert_not_called()
    canvas_mocks.create_default_canvas_cli_dependencies.assert_not_called()
    canvas_mocks.create_canvas_tool.assert_not_called()

    resolver = registration["resolvers"][0]
    assert await resolver("/__openclaw__/canvas/documents/id/index.html") == "/tmp/canvas-asset"
    canvas_mocks.resolve_canvas_http_path_to_local_path.assert_called_once()

    await registration["cli_features"][0]["registrar"](
        {
            "program": {},
            "parent_path": ["nodes"],
            "config": {},
            "workspace_dir": None,
            "logger": SimpleNamespace(
                info=lambda *_args: None,
                warn=lambda *_args: None,
                error=lambda *_args: None,
                debug=lambda *_args: None,
            ),
        }
    )
    canvas_mocks.create_default_canvas_cli_dependencies.assert_called_once()
    canvas_mocks.register_nodes_canvas_commands.assert_called_once()

    tool_factory = registration["tools"][0]
    assert callable(tool_factory)
    tool = tool_factory({"config": {}, "workspace_dir": "/tmp/workspace"})
    assert not isinstance(tool, list)
    assert tool["name"] == "canvas"
    canvas_mocks.create_canvas_tool.assert_not_called()

    await tool["execute"]("tool-call", {"action": "hide"})
    canvas_mocks.create_canvas_tool.assert_called_once_with(
        config={},
        workspace_dir="/tmp/workspace",
    )
    canvas_mocks.tool_execute.assert_called_once_with("tool-call", {"action": "hide"})
