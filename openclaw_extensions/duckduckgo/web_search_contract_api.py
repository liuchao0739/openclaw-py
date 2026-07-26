"""DuckDuckGo API module exposes the plugin public contract."""

from __future__ import annotations

from openclaw_extensions.duckduckgo.src.ddg_search_provider_shared import (
    create_duck_duck_go_web_search_provider_base,
)


def create_duck_duck_go_web_search_provider() -> dict:
    return {
        **create_duck_duck_go_web_search_provider_base(),
        "create_tool": lambda _ctx: None,
    }
