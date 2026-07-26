"""Brave Search contract provider exposes metadata without the runtime search tool."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.brave.web_search_shared import build_brave_web_search_provider_base


def create_brave_web_search_provider() -> dict[str, Any]:
    return {
        **build_brave_web_search_provider_base(),
        "create_tool": lambda _ctx: None,
    }
