"""Diffs Language Pack API module exposes the plugin public contract."""

from openclaw.plugin_sdk.plugin_entry import (
    OpenClawPluginApi,
    PluginLogger,
    define_plugin_entry,
)

__all__ = [
    "OpenClawPluginApi",
    "PluginLogger",
    "define_plugin_entry",
]