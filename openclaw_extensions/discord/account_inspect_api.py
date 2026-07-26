"""Discord API module exposes the plugin public contract."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.discord.src.account_inspect import inspect_discord_account


def inspect_discord_read_only_account(cfg: dict[str, Any], account_id: str | None = None):
    return inspect_discord_account(cfg=cfg, account_id=account_id)


__all__ = ["inspect_discord_read_only_account"]
