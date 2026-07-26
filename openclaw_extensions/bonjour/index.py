"""Bonjour gateway-discovery plugin entry.

Advertises the local gateway over mDNS and lazily loads the ciao-based advertiser.
"""

from __future__ import annotations

import importlib
import re
from collections.abc import Mapping
from typing import Any

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry


def format_bonjour_instance_name(display_name: str) -> str:
    trimmed = display_name.strip()
    if not trimmed:
        return "OpenClaw"
    if re.search(r"openclaw", trimmed, re.IGNORECASE):
        return trimmed
    return f"{trimmed} (OpenClaw)"


def _register(api: OpenClawPluginApi) -> None:
    async def advertise(ctx: Mapping[str, Any]) -> dict[str, Any]:
        advertiser_module = importlib.import_module("openclaw_extensions.bonjour.src.advertiser")
        runtime_module = importlib.import_module("openclaw.plugin_sdk.runtime")
        advertiser = await advertiser_module.start_gateway_bonjour_advertiser(
            {
                "instance_name": format_bonjour_instance_name(str(ctx["machine_display_name"])),
                "gateway_port": ctx["gateway_port"],
                "gateway_tls_enabled": ctx["gateway_tls_enabled"],
                "gateway_tls_fingerprint_sha256": ctx.get("gateway_tls_fingerprint_sha256"),
                "gateway_direct_reachable": ctx["gateway_direct_reachable"],
                "canvas_port": ctx.get("canvas_port"),
                "ssh_port": ctx.get("ssh_port"),
                "tailnet_dns": ctx.get("tailnet_dns"),
                "cli_path": ctx.get("cli_path"),
                "minimal": ctx["minimal"],
            },
            {
                "logger": api.logger,
                "register_uncaught_exception_handler": (
                    runtime_module.register_uncaught_exception_handler
                ),
                "register_unhandled_rejection_handler": (
                    runtime_module.register_unhandled_rejection_handler
                ),
            },
        )
        return {"stop": advertiser["stop"]}

    api.register_gateway_discovery_service(
        {
            "id": "bonjour",
            "advertise": advertise,
        }
    )


default = define_plugin_entry(
    id="bonjour",
    name="Bonjour Gateway Discovery",
    description="Advertise the local OpenClaw gateway over Bonjour/mDNS.",
    register=_register,
)
