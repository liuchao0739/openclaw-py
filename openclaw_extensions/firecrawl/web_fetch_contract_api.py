"""Firecrawl API module exposes the plugin public contract."""

from __future__ import annotations

from openclaw.plugin_sdk.provider_enable_config import enable_plugin_in_config
from openclaw_extensions.firecrawl.src.firecrawl_fetch_provider_shared import (
    FIRECRAWL_WEB_FETCH_PROVIDER_SHARED,
)


def create_firecrawl_web_fetch_provider() -> dict:
    return {
        **FIRECRAWL_WEB_FETCH_PROVIDER_SHARED,
        "apply_selection_config": lambda config: enable_plugin_in_config(config, "firecrawl")[
            "config"
        ],
        "create_tool": lambda _ctx: None,
    }
