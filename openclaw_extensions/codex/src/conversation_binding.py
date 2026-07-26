"""Codex conversation binding hooks."""

from __future__ import annotations

from typing import Any


async def handle_codex_conversation_inbound_claim(_event: Any, _ctx: Any, **_kwargs: Any) -> Any:
    return None


async def handle_codex_conversation_binding_resolved(_event: Any) -> None:
    return None
