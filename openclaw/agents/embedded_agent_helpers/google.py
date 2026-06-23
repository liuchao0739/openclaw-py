"""Google/Gemini-specific embedded-agent runtime helpers."""

from __future__ import annotations

from typing import Any

from openclaw.agents.embedded_agent_helpers.bootstrap import sanitize_google_turn_ordering


def is_google_model_api(api: str | None) -> bool:
    return api in ("google-gemini-cli", "google-generative-ai")

__all__ = ["is_google_model_api", "sanitize_google_turn_ordering"]