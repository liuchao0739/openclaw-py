"""DuckDuckGo plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.duckduckgo.src.ddg_search_provider import (
    create_duck_duck_go_web_search_provider,
)


def _register(api: OpenClawPluginApi) -> None:
    api.register_web_search_provider(create_duck_duck_go_web_search_provider())


default = define_plugin_entry(
    id="duckduckgo",
    name="DuckDuckGo Plugin",
    description="Bundled DuckDuckGo web search plugin",
    register=_register,
)
