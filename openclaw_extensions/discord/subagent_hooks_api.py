"""Discord API module exposes the plugin public contract."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_discord_subagent_hooks_module: Any | None = None


def _load_discord_subagent_hooks_module() -> Any:
    global _discord_subagent_hooks_module
    if _discord_subagent_hooks_module is None:
        _discord_subagent_hooks_module = import_module(
            "openclaw_extensions.discord.src.subagent_hooks"
        )
    return _discord_subagent_hooks_module


def register_discord_subagent_hooks(api: Any) -> None:
    async def on_subagent_ended(event: Any, _ctx: Any = None) -> None:
        module = _load_discord_subagent_hooks_module()
        module.handle_discord_subagent_ended(event)

    async def on_subagent_delivery_target(event: Any, _ctx: Any = None) -> Any:
        module = _load_discord_subagent_hooks_module()
        return module.handle_discord_subagent_delivery_target(event)

    api.on("subagent_ended", on_subagent_ended)
    api.on("subagent_delivery_target", on_subagent_delivery_target)


__all__ = ["register_discord_subagent_hooks"]
