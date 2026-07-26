"""Tests for Discord configured state."""

from __future__ import annotations

from openclaw_extensions.discord.configured_state import has_discord_configured_state


def test_has_discord_configured_state_false_when_missing() -> None:
    assert has_discord_configured_state({"env": {}}) is False
    assert has_discord_configured_state({"env": {"DISCORD_BOT_TOKEN": ""}}) is False
    assert has_discord_configured_state({"env": {"DISCORD_BOT_TOKEN": "   "}}) is False


def test_has_discord_configured_state_true_when_present() -> None:
    assert has_discord_configured_state({"env": {"DISCORD_BOT_TOKEN": "tok"}}) is True
