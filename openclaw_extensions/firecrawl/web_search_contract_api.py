"""Firecrawl API module exposes the plugin public contract."""

from __future__ import annotations

from openclaw_extensions.firecrawl.web_search_shared import build_firecrawl_web_search_provider_base


def create_firecrawl_web_search_provider() -> dict:
    return {
        **build_firecrawl_web_search_provider_base(),
        "create_tool": lambda _ctx: None,
    }
