"""Outbound plugin loader.

Resolves channel outbound adapters from the plugin registry.
"""

from __future__ import annotations

from typing import Any

from openclaw.channels.plugins.outbound.load_types import (
    ChannelPresentationCapabilities,
    OutboundPluginLoadResult,
)


async def load_outbound_plugin(
    channel_id: str,
    config: dict[str, Any] | None = None,
) -> OutboundPluginLoadResult | None:
    """Load an outbound plugin adapter for a channel.

    Deferred to the plugin registry; returns None when unavailable.
    """
    try:
        from openclaw.plugins.plugin_registry import load_plugin_registry_snapshot

        registry = load_plugin_registry_snapshot({"config": config or {}})
        for plugin in registry.get("plugins", []):
            channels = plugin.get("channels", {})
            if isinstance(channels, dict) and channel_id in channels:
                return OutboundPluginLoadResult(
                    pluginId=plugin.get("pluginId", ""),
                    capabilities=ChannelPresentationCapabilities(
                        actions=True, selects=False, text=True, media=True,
                    ),
                    adapter=None,
                )
    except Exception:
        pass
    return None
