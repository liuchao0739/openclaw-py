"""Browser runtime registration barrel."""

from __future__ import annotations

from typing import Any


def create_browser_tool(opts: Any | None = None) -> Any:
    from openclaw_extensions.browser.src.browser_tool import create_browser_tool as impl

    return impl(opts)


async def handle_browser_gateway_request(opts: Any) -> Any:
    from openclaw_extensions.browser.src.gateway.browser_request import (
        handle_browser_gateway_request as impl,
    )

    result = impl(opts)
    if hasattr(result, "__await__"):
        return await result
    return result


async def run_browser_proxy_command(params_json: str) -> Any:
    from openclaw_extensions.browser.src.node_host.invoke_browser import (
        run_browser_proxy_command as impl,
    )

    result = impl(params_json)
    if hasattr(result, "__await__"):
        return await result
    return result


def create_browser_plugin_service() -> Any:
    from openclaw_extensions.browser.src.plugin_service import create_browser_plugin_service as impl

    return impl()


async def collect_browser_security_audit_findings(ctx: Any) -> Any:
    from openclaw_extensions.browser.src.security_audit import (
        collect_browser_security_audit_findings as impl,
    )

    result = impl(ctx)
    if hasattr(result, "__await__"):
        return await result
    return result
