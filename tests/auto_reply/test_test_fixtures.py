"""Tests for auto_reply/reply/test_fixtures — ACP runtime fixtures."""

from __future__ import annotations

from openclaw.auto_reply.reply.test_fixtures import (
    create_acp_session_meta,
    create_acp_test_config,
)


class TestAcpTestConfig:
    def test_defaults(self):
        config = create_acp_test_config()
        assert config["acp"]["enabled"] is True
        assert config["acp"]["stream"]["coalesceIdleMs"] == 0

    def test_overrides(self):
        config = create_acp_test_config({"acp": {"enabled": False}})
        assert config["acp"]["enabled"] is False

    def test_extra_keys(self):
        config = create_acp_test_config({"custom": "value"})
        assert config["custom"] == "value"


class TestAcpSessionMeta:
    def test_defaults(self):
        meta = create_acp_session_meta()
        assert meta["backend"] == "acpx"
        assert meta["agent"] == "codex"
        assert meta["state"] == "idle"
        assert "identity" in meta
        assert meta["identity"]["state"] == "resolved"

    def test_overrides(self):
        meta = create_acp_session_meta({"agent": "claude", "state": "running"})
        assert meta["agent"] == "claude"
        assert meta["state"] == "running"

    def test_has_timestamp(self):
        meta = create_acp_session_meta()
        assert meta["lastActivityAt"] > 0
        assert meta["identity"]["lastUpdatedAt"] > 0
