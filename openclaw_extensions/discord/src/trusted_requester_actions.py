"""Discord guild-admin actions need a Discord sender identity for permission checks."""

from __future__ import annotations

TRUSTED_REQUESTER_GUILD_ADMIN_ACTIONS = {
    "emoji-upload",
    "sticker-upload",
    "role-add",
    "role-remove",
    "channel-create",
    "channel-edit",
    "channel-delete",
    "channel-move",
    "category-create",
    "category-edit",
    "category-delete",
    "event-create",
    "timeout",
    "kick",
    "ban",
}


def is_trusted_requester_guild_admin_action(action: str) -> bool:
    return action in TRUSTED_REQUESTER_GUILD_ADMIN_ACTIONS


__all__ = ["is_trusted_requester_guild_admin_action"]
