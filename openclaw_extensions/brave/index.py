"""Brave plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.brave.src.brave_web_search_provider import create_brave_web_search_provider
from openclaw_extensions.brave.src.config import brave_plugin_config_schema


def _register(api: OpenClawPluginApi) -> None:
    api.register_web_search_provider(create_brave_web_search_provider())


default = define_plugin_entry(
    id="brave",
    name="Brave Plugin",
    description="Bundled Brave plugin",
    config_schema=brave_plugin_config_schema,
    register=_register,
)
