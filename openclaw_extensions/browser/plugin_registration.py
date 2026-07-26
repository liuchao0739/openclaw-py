"""Browser plugin registration helpers."""

from __future__ import annotations

import contextlib
import importlib
import os
from collections.abc import Awaitable, Mapping
from typing import Any

from openclaw.infra.env import is_truthy_env_value
from openclaw_extensions.browser.src.browser_gateway_contract import (
    BROWSER_REQUEST_GATEWAY_METHOD,
    BROWSER_REQUEST_GATEWAY_SCOPE,
)
from openclaw_extensions.browser.src.browser_tool_schema import BrowserToolSchema

EAGER_BROWSER_CONTROL_SERVICE_ENV = "OPENCLAW_EAGER_BROWSER_CONTROL_SERVER"

_browser_registration_runtime_module: Any | None = None

BROWSER_CLI_DESCRIPTOR = {
    "name": "browser",
    "description": "Manage OpenClaw's dedicated browser (Chrome/Chromium)",
    "hasSubcommands": True,
}

browser_plugin_reload = {"restartPrefixes": ["browser"]}


async def _load_browser_registration_runtime_module() -> Any:
    global _browser_registration_runtime_module
    if _browser_registration_runtime_module is None:
        _browser_registration_runtime_module = importlib.import_module(
            "openclaw_extensions.browser.register_runtime"
        )
    return _browser_registration_runtime_module


def _ctx_value(ctx: Any, *keys: str) -> Any:
    for key in keys:
        if isinstance(ctx, Mapping) and key in ctx:
            return ctx[key]
        if hasattr(ctx, key):
            return getattr(ctx, key)
    return None


def _derive_chat_type_from_session_key(session_key: str | None) -> str | None:
    tokens = {
        token
        for token in (session_key or "").lower().split(":")
        if token
    }
    if "group" in tokens:
        return "group"
    if "channel" in tokens:
        return "channel"
    if "direct" in tokens or "dm" in tokens:
        return "direct"
    return None


def _browser_tool_description(*, target_default: str, host_hint: str) -> str:
    return " ".join(
        [
            (
                "Control the browser via OpenClaw's browser control server "
                "(status/start/stop/profiles/tabs/open/snapshot/screenshot/actions)."
            ),
            (
                "Browser choice: omit profile by default for the isolated OpenClaw-managed "
                "browser (`openclaw`)."
            ),
            (
                'For the logged-in user browser, use profile="user". A supported '
                "Chromium-based browser (v144+) must be running on the selected host or "
                "browser node. Use only when existing logins/cookies matter and the user "
                "is present."
            ),
            (
                'For profile="user" or other existing-session profiles, omit timeoutMs on '
                "act:type, evaluate, hover, scrollIntoView, drag, select, and fill; that "
                "driver rejects per-call timeout overrides for those actions."
            ),
            (
                "When a node-hosted browser proxy is available, the tool may auto-route to it. "
                'Pin a node with node=<id|name> or target="node".'
            ),
            (
                "When using refs from snapshot (e.g. e12), keep the same tab: prefer passing "
                "targetId from the snapshot response into subsequent actions "
                "(act/click/type/etc). For tab operations, targetId also accepts tabId "
                "handles (t1) and labels from action=tabs."
            ),
            (
                "For multi-step browser work, login checks, stale refs, duplicate tabs, or "
                "Google Meet flows, use the bundled browser-automation skill when it is available."
            ),
            (
                'For stable, self-resolving refs across calls, use snapshot with refs="aria" '
                '(Playwright aria-ref ids). Default refs="role" are role+name-based.'
            ),
            (
                "Use snapshot+act for UI automation. Avoid act:wait by default; use only in "
                "exceptional cases when no reliable UI state exists."
            ),
            f"target selects browser location (sandbox|host|node). Default: {target_default}.",
            host_hint,
        ]
    )


def create_lazy_browser_tool(opts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    options = dict(opts or {})
    target_default = "sandbox" if options.get("sandboxBridgeUrl") else "host"
    allow_host_control = options.get("allowHostControl")
    host_hint = (
        "Host target blocked by policy."
        if allow_host_control is False
        else "Host target allowed."
    )

    async def execute(tool_call_id: Any, args: Any, signal: Any = None, on_update: Any = None) -> Any:
        runtime = await _load_browser_registration_runtime_module()
        tool = runtime.create_browser_tool(options)
        result = tool.execute(tool_call_id, args, signal, on_update)
        if isinstance(result, Awaitable):
            return await result
        return result

    return {
        "label": "Browser",
        "name": "browser",
        "description": _browser_tool_description(
            target_default=target_default,
            host_hint=host_hint,
        ),
        "parameters": BrowserToolSchema,
        "execute": execute,
    }


def create_browser_tool_options(ctx: Any) -> dict[str, Any]:
    browser = _ctx_value(ctx, "browser")
    browser_mapping = browser if isinstance(browser, Mapping) else {}
    session_key = _ctx_value(ctx, "sessionKey", "session_key")
    agent_dir = _ctx_value(ctx, "agentDir", "agent_dir")
    workspace_dir = _ctx_value(ctx, "workspaceDir", "workspace_dir")
    active_model = _ctx_value(ctx, "activeModel", "active_model")
    delivery_context = _ctx_value(ctx, "deliveryContext", "delivery_context")
    message_channel = _ctx_value(ctx, "messageChannel", "message_channel")

    media_channel = None
    if isinstance(delivery_context, Mapping):
        media_channel = delivery_context.get("channel")
    if media_channel is None:
        media_channel = message_channel

    media_chat_type = _derive_chat_type_from_session_key(
        str(session_key) if session_key is not None else None
    )

    options: dict[str, Any] = {}
    sandbox_bridge_url = browser_mapping.get("sandboxBridgeUrl")
    if sandbox_bridge_url:
        options["sandboxBridgeUrl"] = sandbox_bridge_url
    if "allowHostControl" in browser_mapping:
        options["allowHostControl"] = browser_mapping["allowHostControl"]
    if session_key:
        options["agentSessionKey"] = session_key
    if agent_dir:
        options["agentDir"] = agent_dir
    if workspace_dir:
        options["workspaceDir"] = workspace_dir

    if isinstance(active_model, Mapping) and (
        active_model.get("provider") or active_model.get("modelId") or active_model.get("model")
    ):
        options["activeModel"] = {
            "provider": active_model.get("provider"),
            "model": active_model.get("modelId") or active_model.get("model"),
        }

    if session_key or media_channel:
        media_scope: dict[str, Any] = {}
        if session_key:
            media_scope["sessionKey"] = session_key
        if media_channel:
            media_scope["channel"] = media_channel
        if media_chat_type:
            media_scope["chatType"] = media_chat_type
        options["mediaScope"] = media_scope

    return options


async def _handle_browser_proxy_command(params_json: str) -> Any:
    runtime = await _load_browser_registration_runtime_module()
    return await runtime.run_browser_proxy_command(params_json)


async def _collect_browser_security_audit(ctx: Any) -> Any:
    runtime = await _load_browser_registration_runtime_module()
    return await runtime.collect_browser_security_audit_findings(ctx)


browser_plugin_node_host_commands = [
    {
        "command": "browser.proxy",
        "cap": "browser",
        "handle": _handle_browser_proxy_command,
    }
]

browser_security_audit_collectors = [_collect_browser_security_audit]


def _create_lazy_browser_plugin_service() -> Any:
    service: Any | None = None

    async def load_service() -> Any:
        nonlocal service
        if service is None:
            runtime = await _load_browser_registration_runtime_module()
            service = runtime.create_browser_plugin_service()
        return service

    class LazyBrowserPluginService:
        id = "browser-control"

        async def start(self, ctx: Any) -> None:
            if not is_truthy_env_value(os.environ.get(EAGER_BROWSER_CONTROL_SERVICE_ENV)):
                return
            loaded = await load_service()
            result = loaded.start(ctx)
            if isinstance(result, Awaitable):
                await result

        async def stop(self, ctx: Any) -> None:
            nonlocal service
            if service is None:
                control_service = importlib.import_module(
                    "openclaw_extensions.browser.src.control_service"
                )
                with contextlib.suppress(Exception):
                    result = control_service.stop_browser_control_service()
                    if isinstance(result, Awaitable):
                        await result
                return
            stop = getattr(service, "stop", None)
            if stop is None:
                return
            result = stop(ctx)
            if isinstance(result, Awaitable):
                await result

    return LazyBrowserPluginService()


def register_browser_plugin(api: Any) -> None:
    api.register_tool(  # type: ignore[attr-defined]
        lambda ctx: create_lazy_browser_tool(create_browser_tool_options(ctx))
    )

    async def register_browser_cli(ctx: Any) -> None:
        cli_module = importlib.import_module("openclaw_extensions.browser.src.cli.browser_cli")
        program = ctx["program"] if isinstance(ctx, Mapping) else ctx.program
        cli_module.register_browser_cli(program)

    api.register_cli(  # type: ignore[attr-defined]
        register_browser_cli,
        {"commands": ["browser"], "descriptors": [BROWSER_CLI_DESCRIPTOR]},
    )

    async def handle_browser_gateway_request(opts: Any) -> Any:
        runtime = await _load_browser_registration_runtime_module()
        return await runtime.handle_browser_gateway_request(opts)

    api.register_gateway_method(  # type: ignore[attr-defined]
        BROWSER_REQUEST_GATEWAY_METHOD,
        handle_browser_gateway_request,
        {"scope": BROWSER_REQUEST_GATEWAY_SCOPE},
    )
    api.register_service(_create_lazy_browser_plugin_service())  # type: ignore[arg-type]
