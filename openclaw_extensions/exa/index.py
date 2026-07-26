"""Exa plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.exa.src.exa_web_search_provider import create_exa_web_search_provider


def _register(api: OpenClawPluginApi) -> None:
    api.register_web_search_provider(create_exa_web_search_provider())


default = define_plugin_entry(
    id="exa",
    name="Exa Plugin",
    description="Bundled Exa web search plugin",
    register=_register,
)
