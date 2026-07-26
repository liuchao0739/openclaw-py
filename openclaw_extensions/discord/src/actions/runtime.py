"""Discord plugin module implements runtime behavior."""

from __future__ import annotations

from typing import Any


async def handle_discord_action(
    params: dict[str, Any],
    cfg: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raise NotImplementedError(
        "Discord action runtime is not fully ported yet; use mocks in tests or wire the gateway runtime."
    )


__all__ = ["handle_discord_action"]
