"""Contract web search provider entry for Codex."""

from __future__ import annotations

from openclaw_extensions.codex.src.web_search_provider_shared import (
    create_codex_web_search_provider_base,
)


def create_codex_web_search_provider() -> dict:
    return {
        **create_codex_web_search_provider_base(),
        "createTool": lambda _ctx=None: None,
    }
