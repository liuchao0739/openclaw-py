"""Tests for the browser extension plugin entry."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from openclaw_extensions.browser.plugin_registration import (
    browser_plugin_node_host_commands,
    browser_plugin_reload,
    browser_security_audit_collectors,
    register_browser_plugin,
)
from openclaw_extensions.browser.test_fetch import with_browser_fetch_preconnect

EXTENSION_ROOT = Path(__file__).resolve().parents[2] / "openclaw_extensions" / "browser"


@pytest.fixture
def runtime_api_mocks(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    mocks = SimpleNamespace(
        create_browser_plugin_service=MagicMock(
            return_value=SimpleNamespace(id="browser-control", start=AsyncMock())
        ),
        create_browser_tool=MagicMock(
            return_value=SimpleNamespace(
                execute=AsyncMock(return_value={"type": "json", "value": {"ok": True}}),
            )
        ),
        collect_browser_security_audit_findings=AsyncMock(return_value=[]),
        handle_browser_gateway_request=AsyncMock(),
        register_browser_cli=MagicMock(),
        run_browser_proxy_command=AsyncMock(return_value="ok"),
        stop_browser_control_service=AsyncMock(return_value=None),
    )

    control_service_module = ModuleType("openclaw_extensions.browser.src.control_service")
    control_service_module.stop_browser_control_service = mocks.stop_browser_control_service

    browser_cli_module = ModuleType("openclaw_extensions.browser.src.cli.browser_cli")
    browser_cli_module.register_browser_cli = mocks.register_browser_cli

    monkeypatch.setitem(
        sys.modules,
        "openclaw_extensions.browser.src.control_service",
        control_service_module,
    )
    monkeypatch.setitem(
        sys.modules,
        "openclaw_extensions.browser.src.cli.browser_cli",
        browser_cli_module,
    )

    register_runtime = importlib.import_module("openclaw_extensions.browser.register_runtime")
    monkeypatch.setattr(
        register_runtime,
        "create_browser_plugin_service",
        mocks.create_browser_plugin_service,
    )
    monkeypatch.setattr(register_runtime, "create_browser_tool", mocks.create_browser_tool)
    monkeypatch.setattr(
        register_runtime,
        "collect_browser_security_audit_findings",
        mocks.collect_browser_security_audit_findings,
    )
    monkeypatch.setattr(
        register_runtime,
        "handle_browser_gateway_request",
        mocks.handle_browser_gateway_request,
    )
    monkeypatch.setattr(
        register_runtime, "run_browser_proxy_command", mocks.run_browser_proxy_command
    )

    plugin_registration = importlib.import_module("openclaw_extensions.browser.plugin_registration")
    plugin_registration._browser_registration_runtime_module = None

    return mocks


def _create_api() -> dict[str, Any]:
    register_cli = MagicMock()
    register_gateway_method = MagicMock()
    register_service = MagicMock()
    register_tool = MagicMock()

    class FakeApi:
        def register_cli(self, registrar: Any, opts: Any) -> None:
            register_cli(registrar, opts)

        def register_gateway_method(self, method: Any, handler: Any, opts: Any) -> None:
            register_gateway_method(method, handler, opts)

        def register_service(self, service: Any) -> None:
            register_service(service)

        def register_tool(self, tool: Any) -> None:
            register_tool(tool)

    return {
        "api": FakeApi(),
        "register_cli": register_cli,
        "register_gateway_method": register_gateway_method,
        "register_service": register_service,
        "register_tool": register_tool,
    }


def _mock_call_arg(mock: MagicMock, index: int = 0, arg_index: int = 0) -> Any:
    call = mock.call_args_list[index]
    return call.args[arg_index]


def _register_browser_auto_enable_probe() -> Any:
    probes: list[Any] = []
    setup_api = importlib.import_module("openclaw_extensions.browser.setup_api")

    class FakeApi:
        def register_auto_enable_probe(self, probe: Any) -> None:
            probes.append(probe)

    setup_api.default.register(FakeApi())
    if not probes:
        raise AssertionError("expected browser setup plugin to register an auto-enable probe")
    return probes[0]


def test_exposes_static_browser_metadata() -> None:
    assert browser_plugin_reload == {"restartPrefixes": ["browser"]}
    assert len(browser_plugin_node_host_commands) == 1
    assert browser_plugin_node_host_commands[0]["command"] == "browser.proxy"
    assert browser_plugin_node_host_commands[0]["cap"] == "browser"
    assert callable(browser_plugin_node_host_commands[0]["handle"])
    assert len(browser_security_audit_collectors) == 1


def test_bundles_browser_automation_skill() -> None:
    manifest = json.loads((EXTENSION_ROOT / "openclaw.plugin.json").read_text(encoding="utf-8"))
    skill_path = EXTENSION_ROOT / "skills" / "browser-automation" / "SKILL.md"

    assert manifest["skills"] == ["./skills"]
    assert "name: browser-automation" in skill_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_keeps_tool_registration_sync_while_loading_runtime_on_execute(
    runtime_api_mocks: SimpleNamespace,
) -> None:
    api_bundle = _create_api()
    register_browser_plugin(api_bundle["api"])

    factory = _mock_call_arg(api_bundle["register_tool"])
    tool = factory(
        {
            "sessionKey": "agent:main:webchat:direct:123",
            "browser": {
                "sandboxBridgeUrl": "http://127.0.0.1:9999",
                "allowHostControl": True,
            },
        }
    )
    assert not isinstance(tool, list)
    assert tool["name"] == "browser"
    runtime_api_mocks.create_browser_tool.assert_not_called()

    await tool["execute"]("call-1", {"action": "status"})
    runtime_api_mocks.create_browser_tool.assert_called_once_with(
        {
            "sandboxBridgeUrl": "http://127.0.0.1:9999",
            "allowHostControl": True,
            "agentSessionKey": "agent:main:webchat:direct:123",
            "mediaScope": {
                "sessionKey": "agent:main:webchat:direct:123",
                "chatType": "direct",
            },
        }
    )


@pytest.mark.asyncio
async def test_passes_runtime_context_for_screenshot_image_understanding(
    runtime_api_mocks: SimpleNamespace,
) -> None:
    api_bundle = _create_api()
    register_browser_plugin(api_bundle["api"])

    factory = _mock_call_arg(api_bundle["register_tool"])
    tool = factory(
        {
            "sessionKey": "agent:main:webchat:direct:123",
            "agentDir": "/tmp/agent",
            "workspaceDir": "/tmp/workspace",
            "activeModel": {"provider": "openai", "modelId": "gpt-5.5"},
            "deliveryContext": {"channel": "telegram"},
        }
    )
    assert not isinstance(tool, list)

    await tool["execute"]("call-1", {"action": "status"})
    runtime_api_mocks.create_browser_tool.assert_called_once_with(
        {
            "agentSessionKey": "agent:main:webchat:direct:123",
            "agentDir": "/tmp/agent",
            "workspaceDir": "/tmp/workspace",
            "activeModel": {"provider": "openai", "model": "gpt-5.5"},
            "mediaScope": {
                "sessionKey": "agent:main:webchat:direct:123",
                "channel": "telegram",
                "chatType": "direct",
            },
        }
    )


@pytest.mark.asyncio
async def test_derives_group_chat_type_for_browser_media_scope(
    runtime_api_mocks: SimpleNamespace,
) -> None:
    api_bundle = _create_api()
    register_browser_plugin(api_bundle["api"])

    factory = _mock_call_arg(api_bundle["register_tool"])
    tool = factory(
        {
            "sessionKey": "agent:main:telegram:group:chat-123",
            "messageChannel": "telegram",
        }
    )
    assert not isinstance(tool, list)

    await tool["execute"]("call-1", {"action": "status"})
    runtime_api_mocks.create_browser_tool.assert_called_once_with(
        {
            "agentSessionKey": "agent:main:telegram:group:chat-123",
            "mediaScope": {
                "sessionKey": "agent:main:telegram:group:chat-123",
                "channel": "telegram",
                "chatType": "group",
            },
        }
    )


@pytest.mark.asyncio
async def test_registers_cli_descriptors_and_lazy_loads_browser_cli(
    runtime_api_mocks: SimpleNamespace,
) -> None:
    api_bundle = _create_api()
    register_browser_plugin(api_bundle["api"])

    api_bundle["register_cli"].assert_called_once()
    registrar = _mock_call_arg(api_bundle["register_cli"])
    assert callable(registrar)
    assert _mock_call_arg(api_bundle["register_cli"], arg_index=1) == {
        "commands": ["browser"],
        "descriptors": [
            {
                "name": "browser",
                "description": "Manage OpenClaw's dedicated browser (Chrome/Chromium)",
                "hasSubcommands": True,
            }
        ],
    }

    await registrar({"program": {}})
    runtime_api_mocks.register_browser_cli.assert_called_once_with({})


@pytest.mark.asyncio
async def test_registers_browser_request_gateway_method_and_lazy_loads_handler(
    runtime_api_mocks: SimpleNamespace,
) -> None:
    api_bundle = _create_api()
    register_browser_plugin(api_bundle["api"])

    api_bundle["register_gateway_method"].assert_called_once()
    assert _mock_call_arg(api_bundle["register_gateway_method"]) == "browser.request"
    handler = _mock_call_arg(api_bundle["register_gateway_method"], arg_index=1)
    assert callable(handler)
    assert _mock_call_arg(api_bundle["register_gateway_method"], arg_index=2) == {
        "scope": "operator.admin",
    }

    await handler({"method": "browser.request"})
    runtime_api_mocks.handle_browser_gateway_request.assert_called_once_with(
        {"method": "browser.request"}
    )


@pytest.mark.asyncio
async def test_lazy_loads_node_host_and_audit_runtime_handlers(
    runtime_api_mocks: SimpleNamespace,
) -> None:
    assert await browser_plugin_node_host_commands[0]["handle"]("{}") == "ok"
    runtime_api_mocks.run_browser_proxy_command.assert_called_once_with("{}")

    assert await browser_security_audit_collectors[0]({}) == []
    runtime_api_mocks.collect_browser_security_audit_findings.assert_called_once()


@pytest.mark.asyncio
async def test_registers_lazy_browser_control_service(
    runtime_api_mocks: SimpleNamespace,
) -> None:
    api_bundle = _create_api()
    register_browser_plugin(api_bundle["api"])

    service = _mock_call_arg(api_bundle["register_service"])
    assert service.id == "browser-control"
    assert callable(service.start)
    assert callable(service.stop)
    runtime_api_mocks.create_browser_plugin_service.assert_not_called()

    await service.start(
        {"config": {}, "stateDir": "/tmp/openclaw", "logger": {"warn": MagicMock()}}
    )
    runtime_api_mocks.create_browser_plugin_service.assert_not_called()

    await service.stop({"config": {}, "stateDir": "/tmp/openclaw", "logger": {"warn": MagicMock()}})
    runtime_api_mocks.stop_browser_control_service.assert_called_once()


@pytest.mark.asyncio
async def test_eager_loads_browser_control_service_when_requested(
    runtime_api_mocks: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENCLAW_EAGER_BROWSER_CONTROL_SERVER", "1")
    api_bundle = _create_api()
    register_browser_plugin(api_bundle["api"])

    service = _mock_call_arg(api_bundle["register_service"])
    await service.start(
        {"config": {}, "stateDir": "/tmp/openclaw", "logger": {"warn": MagicMock()}}
    )
    runtime_api_mocks.create_browser_plugin_service.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["false", "", "disabled"])
async def test_keeps_browser_control_service_env_value_lazy(
    value: str,
    runtime_api_mocks: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENCLAW_EAGER_BROWSER_CONTROL_SERVER", value)
    api_bundle = _create_api()
    register_browser_plugin(api_bundle["api"])

    service = _mock_call_arg(api_bundle["register_service"])
    await service.start(
        {"config": {}, "stateDir": "/tmp/openclaw", "logger": {"warn": MagicMock()}}
    )
    runtime_api_mocks.create_browser_plugin_service.assert_not_called()


def test_declares_setup_auto_enable_reasons_for_browser_config_surfaces() -> None:
    probe = _register_browser_auto_enable_probe()

    assert probe({"config": {"browser": {"defaultProfile": "openclaw"}}, "env": {}}) == (
        "browser configured"
    )
    assert probe({"config": {"tools": {"alsoAllow": ["browser"]}}, "env": {}}) == (
        "browser tool referenced"
    )
    assert (
        probe(
            {
                "config": {"browser": {"defaultProfile": "openclaw", "enabled": False}},
                "env": {},
            }
        )
        is None
    )


def test_with_browser_fetch_preconnect_adds_metadata() -> None:
    fetch_mock = MagicMock()
    wrapped = with_browser_fetch_preconnect(fetch_mock)
    assert wrapped is fetch_mock
    assert callable(fetch_mock.preconnect)
    assert fetch_mock.__openclawAcceptsDispatcher is True
    fetch_mock.preconnect("https://example.com")
    fetch_dict: dict[str, Any] = {"fetch": fetch_mock}
    wrapped_dict = with_browser_fetch_preconnect(fetch_dict)
    assert wrapped_dict is fetch_dict
    assert callable(fetch_dict["preconnect"])
    assert fetch_dict["__openclawAcceptsDispatcher"] is True
