"""Exa API module exposes the plugin public contract."""

from __future__ import annotations

from openclaw_extensions.exa.src.exa_web_search_provider_shared import (
    create_exa_web_search_provider_base,
)


def create_exa_web_search_provider() -> dict:
    return {
        **create_exa_web_search_provider_base(),
        "create_tool": lambda _ctx: None,
    }
