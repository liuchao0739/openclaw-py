"""Diffs API module exposes the plugin public contract."""

from __future__ import annotations

from typing import Any

from openclaw.config.models import OpenClawConfig
from openclaw.mcp import AnyAgentTool
from openclaw.plugin_sdk.plugin_entry import (
    OpenClawPluginApi,
    PluginLogger,
    define_plugin_entry,
)
from openclaw.plugin_sdk.temp_path import resolve_preferred_openclaw_tmp_dir

OpenClawPluginConfigSchema = Any
OpenClawPluginToolContext = Any

__all__ = [
    "AnyAgentTool",
    "OpenClawConfig",
    "OpenClawPluginApi",
    "OpenClawPluginConfigSchema",
    "OpenClawPluginToolContext",
    "PluginLogger",
    "define_plugin_entry",
    "resolve_preferred_openclaw_tmp_dir",
]
