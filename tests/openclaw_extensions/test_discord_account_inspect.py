"""Tests for Discord account inspect API."""

from __future__ import annotations

from openclaw_extensions.discord.account_inspect_api import inspect_discord_read_only_account


def test_inspect_discord_read_only_account_from_config_token(monkeypatch) -> None:
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    cfg = {"channels": {"discord": {"token": "tok"}}}
    result = inspect_discord_read_only_account(cfg)
    assert result.configured is True
    assert result.token == "tok"
    assert result.token_source == "config"


def test_inspect_discord_read_only_account_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "envtok")
    cfg = {"channels": {"discord": {}}}
    result = inspect_discord_read_only_account(cfg)
    assert result.configured is True
    assert result.token == "envtok"
    assert result.token_source == "env"
