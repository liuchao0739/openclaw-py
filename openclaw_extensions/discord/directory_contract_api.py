"""Discord API module exposes the plugin public contract."""

from __future__ import annotations

from openclaw_extensions.discord.src.directory_config import (
    list_discord_directory_groups_from_config,
    list_discord_directory_peers_from_config,
)

discord_directory_contract_plugin = {
    "id": "discord",
    "directory": {
        "listPeers": list_discord_directory_peers_from_config,
        "listGroups": list_discord_directory_groups_from_config,
    },
}

__all__ = [
    "discord_directory_contract_plugin",
    "list_discord_directory_groups_from_config",
    "list_discord_directory_peers_from_config",
]
