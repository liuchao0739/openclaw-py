"""Discord API module exposes the plugin public contract."""

from __future__ import annotations

from typing import Any


async def handle_discord_action(
    params: dict[str, Any],
    cfg: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from openclaw_extensions.discord.src.actions.runtime import handle_discord_action as _handle

    return await _handle(params, cfg, options)


__all__ = ["handle_discord_action"]
