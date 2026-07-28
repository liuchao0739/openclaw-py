from __future__ import annotations

from typing import Any


class PluginChannelRuntimeContext:
    def __init__(
        self,
        channel_id: str,
        plugin_id: str,
        config: dict[str, Any] | None = None,
    ):
        self.channel_id = channel_id
        self.plugin_id = plugin_id
        self.config = config or {}
        self.state: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "channelId": self.channel_id,
            "pluginId": self.plugin_id,
            "config": self.config,
            "state": self.state,
        }


def resolve_channel_runtime_context(
    channel_id: str,
    plugin_id: str,
    config: dict[str, Any] | None = None,
) -> PluginChannelRuntimeContext:
    return PluginChannelRuntimeContext(channel_id, plugin_id, config)
