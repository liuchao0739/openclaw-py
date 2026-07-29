import os
from typing import Any, Optional

from .browser_tool_schema import BrowserToolSchema
from .gateway_contract import BROWSER_REQUEST_GATEWAY_METHOD, BROWSER_REQUEST_GATEWAY_SCOPE
from .browser_tool import (
    _is_truthy_env_value,
    _derive_chat_type_from_session_key,
    create_browser_tool,
    _EAGER_BROWSER_CONTROL_SERVICE_ENV,
)

_BROWSER_CLI_DESCRIPTOR = {
    "name": "browser",
    "description": "Manage OpenClaw's dedicated browser (Chrome/Chromium)",
    "hasSubcommands": True,
}

browserPluginReload = {"restartPrefixes": ["browser"]}

browserPluginNodeHostCommands = [
    {
        "command": "browser.proxy",
        "cap": "browser",
        "handle": lambda paramsJSON: _run_browser_proxy_command(paramsJSON),
    },
]

browserSecurityAuditCollectors = [
    lambda ctx: _collect_browser_security_audit_findings(ctx),
]


async def _run_browser_proxy_command(paramsJSON: str) -> Any:
    raise NotImplementedError("browser proxy command runtime not available")


async def _collect_browser_security_audit_findings(ctx: dict) -> list:
    return []


def _create_browser_tool_options(ctx: dict) -> dict:
    media_channel = (ctx.get("deliveryContext") or {}).get("channel") if isinstance(ctx.get("deliveryContext"), dict) else None
    media_channel = media_channel or ctx.get("messageChannel")
    media_chat_type = _derive_chat_type_from_session_key(ctx.get("sessionKey"))
    opts: dict = {}
    browser_ctx = ctx.get("browser") or {}
    if isinstance(browser_ctx, dict):
        if browser_ctx.get("sandboxBridgeUrl"):
            opts["sandboxBridgeUrl"] = browser_ctx["sandboxBridgeUrl"]
        if browser_ctx.get("allowHostControl") is not None:
            opts["allowHostControl"] = browser_ctx["allowHostControl"]
    if ctx.get("sessionKey"):
        opts["agentSessionKey"] = ctx["sessionKey"]
    if ctx.get("agentDir"):
        opts["agentDir"] = ctx["agentDir"]
    if ctx.get("workspaceDir"):
        opts["workspaceDir"] = ctx["workspaceDir"]
    active_model = ctx.get("activeModel") or {}
    if isinstance(active_model, dict):
        if active_model.get("provider") or active_model.get("modelId"):
            opts["activeModel"] = {
                "provider": active_model.get("provider"),
                "model": active_model.get("modelId"),
            }
    if ctx.get("sessionKey") or media_channel:
        media_scope: dict = {}
        if ctx.get("sessionKey"):
            media_scope["sessionKey"] = ctx["sessionKey"]
        if media_channel:
            media_scope["channel"] = media_channel
        if media_chat_type:
            media_scope["chatType"] = media_chat_type
        opts["mediaScope"] = media_scope
    return opts


def _create_lazy_browser_tool(opts: Optional[dict] = None) -> dict:
    target_default = "sandbox" if (opts or {}).get("sandboxBridgeUrl") else "host"
    host_hint = "Host target blocked by policy." if (opts or {}).get("allowHostControl") is False else "Host target allowed."
    description = " ".join([
        "Control the browser via OpenClaw's browser control server (status/start/stop/profiles/tabs/open/snapshot/screenshot/actions).",
        "Browser choice: omit profile by default for the isolated OpenClaw-managed browser (`openclaw`).",
        'For the logged-in user browser, use profile="user".',
        f"target selects browser location (sandbox|host|node). Default: {target_default}.",
        host_hint,
    ])

    async def execute(*args, **kwargs):
        tool = create_browser_tool(opts)
        return await tool["execute"](*args, **kwargs)

    return {
        "label": "Browser",
        "name": "browser",
        "description": description,
        "parameters": BrowserToolSchema,
        "execute": execute,
    }


def _create_lazy_browser_plugin_service() -> dict:
    service: Optional[dict] = None

    async def start(ctx: dict) -> None:
        nonlocal service
        if not _is_truthy_env_value(os.environ.get(_EAGER_BROWSER_CONTROL_SERVICE_ENV)):
            return
        if service is None:
            service = {"started": True}
        await service.get("start", lambda c: None)(ctx) if callable(service.get("start")) else None

    async def stop(ctx: dict) -> None:
        nonlocal service
        if service is None:
            return
        stop_fn = service.get("stop")
        if callable(stop_fn):
            await stop_fn(ctx)

    return {
        "id": "browser-control",
        "start": start,
        "stop": stop,
    }


def register_browser_plugin(api: dict) -> None:
    def tool_factory(ctx: dict) -> dict:
        return _create_lazy_browser_tool(_create_browser_tool_options(ctx))
    api["registerTool"](tool_factory)
    api["registerCli"](
        lambda ctx: None,
        {"commands": ["browser"], "descriptors": [_BROWSER_CLI_DESCRIPTOR]},
    )
    api["registerGatewayMethod"](
        BROWSER_REQUEST_GATEWAY_METHOD,
        lambda opts: _handle_browser_gateway_request(opts),
        {"scope": BROWSER_REQUEST_GATEWAY_SCOPE},
    )
    api["registerService"](_create_lazy_browser_plugin_service())


async def _handle_browser_gateway_request(opts: dict) -> Any:
    raise NotImplementedError("browser gateway request runtime not available")
