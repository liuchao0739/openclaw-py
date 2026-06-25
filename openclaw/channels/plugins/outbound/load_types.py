"""Load type definitions for outbound plugin loading."""

from __future__ import annotations

from typing import Any, TypedDict


class ChannelPresentationCapabilities(TypedDict, total=False):
    actions: bool
    selects: bool
    text: bool
    media: bool
    limits: dict[str, Any]


class OutboundPluginLoadResult(TypedDict, total=False):
    pluginId: str
    capabilities: ChannelPresentationCapabilities
    adapter: Any
