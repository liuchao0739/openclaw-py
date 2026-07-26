"""Firecrawl plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.firecrawl.src.firecrawl_fetch_provider import (
    create_firecrawl_web_fetch_provider,
)
from openclaw_extensions.firecrawl.src.firecrawl_scrape_tool import create_firecrawl_scrape_tool
from openclaw_extensions.firecrawl.src.firecrawl_search_provider import (
    create_firecrawl_web_search_provider,
)
from openclaw_extensions.firecrawl.src.firecrawl_search_tool import create_firecrawl_search_tool


def _register(api: OpenClawPluginApi) -> None:
    api.register_web_fetch_provider(create_firecrawl_web_fetch_provider())  # type: ignore[attr-defined]
    api.register_web_search_provider(create_firecrawl_web_search_provider())
    api.register_tool(create_firecrawl_search_tool(api))  # type: ignore[attr-defined]
    api.register_tool(create_firecrawl_scrape_tool(api))  # type: ignore[attr-defined]


default = define_plugin_entry(
    id="firecrawl",
    name="Firecrawl Plugin",
    description="Bundled Firecrawl search and scrape plugin",
    register=_register,
)
