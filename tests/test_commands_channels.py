"""Tests for commands/channels — runtime label and add mutators."""

from __future__ import annotations

from openclaw.commands.channels import (
    apply_account_name,
    apply_channel_account_config,
    channel_label,
)


class TestChannelLabel:
    def test_no_plugin_returns_channel(self):
        assert channel_label("unknown-channel") == "unknown-channel"

    def test_with_plugin_label(self):
        import openclaw.commands.channels.runtime_label as mod

        original = mod._get_channel_plugin
        mod._get_channel_plugin = lambda ch: {"meta": {"label": "Telegram"}}
        try:
            assert channel_label("telegram") == "Telegram"
        finally:
            mod._get_channel_plugin = original


class TestApplyAccountName:
    def test_no_plugin_returns_cfg_unchanged(self):
        cfg = {"channels": {}}
        result = apply_account_name(cfg, "test", "acc1", "My Account")
        assert result is cfg

    def test_with_plugin_apply(self):
        cfg = {"channels": {}}
        plugin = {
            "setup": {
                "applyAccountName": lambda params: {
                    **params["cfg"],
                    "channels": {params["accountId"]: {"name": params["name"]}},
                },
            },
        }
        result = apply_account_name(cfg, "test", "acc1", "My Account", plugin=plugin)
        assert "acc1" in result["channels"]
        assert result["channels"]["acc1"]["name"] == "My Account"

    def test_default_account_id(self):
        cfg = {}
        result = apply_account_name(cfg, "test", "", "name")
        assert result is cfg  # No plugin, returns unchanged


class TestApplyChannelAccountConfig:
    def test_no_plugin_returns_cfg_unchanged(self):
        cfg = {"channels": {}}
        result = apply_channel_account_config(cfg, "test", "acc1", {"token": "secret"})
        assert result is cfg

    def test_with_plugin_apply(self):
        cfg = {"channels": {}}
        plugin = {
            "setup": {
                "applyAccountConfig": lambda params: {
                    **params["cfg"],
                    "channels": {params["accountId"]: params["input"]},
                },
            },
        }
        result = apply_channel_account_config(cfg, "test", "acc1", {"token": "secret"}, plugin=plugin)
        assert result["channels"]["acc1"]["token"] == "secret"
