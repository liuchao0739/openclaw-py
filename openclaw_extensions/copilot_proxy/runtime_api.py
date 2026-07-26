"""Copilot Proxy API module exposes the plugin public contract."""

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry

__all__ = [
    "OpenClawPluginApi",
    "define_plugin_entry",
]
