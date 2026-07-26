"""Tests for Discord directory contract plugin."""

from __future__ import annotations

import pytest

from openclaw_extensions.discord.directory_contract_api import discord_directory_contract_plugin


@pytest.mark.asyncio
async def test_discord_directory_contract_plugin_lists_peers_and_groups() -> None:
    cfg = {
        "channels": {
            "discord": {
                "dm": {"allowFrom": ["<@123>", "user:456"]},
                "dms": {"789": {}},
                "guilds": {
                    "g1": {
                        "users": ["user:111"],
                        "channels": {"222": {"users": ["333"]}},
                    }
                },
            }
        }
    }
    plugin = discord_directory_contract_plugin
    assert plugin["id"] == "discord"
    peers = await plugin["directory"]["listPeers"]({"cfg": cfg})
    groups = await plugin["directory"]["listGroups"]({"cfg": cfg})
    assert {"kind": "user", "id": "user:123"} in peers
    assert {"kind": "user", "id": "user:456"} in peers
    assert {"kind": "user", "id": "user:789"} in peers
    assert {"kind": "user", "id": "user:111"} in peers
    assert {"kind": "user", "id": "user:333"} in peers
    assert {"kind": "group", "id": "channel:222"} in groups
