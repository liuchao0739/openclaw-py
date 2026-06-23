"""Bootstrap / Google turn ordering re-exports for embedded agent helpers."""

from __future__ import annotations

from typing import Any

from openclaw.shared.google_turn_ordering import sanitize_google_assistant_first_ordering


def sanitize_google_turn_ordering(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sanitize_google_assistant_first_ordering(messages)