"""Tests for commands/agent — session key helpers."""

from __future__ import annotations

from openclaw.commands.agent import (
    build_explicit_session_id_session_key,
    resolve_session_key_for_request,
)


class TestBuildSessionKey:
    def test_basic(self):
        key = build_explicit_session_id_session_key("main", "session-1")
        assert key == "agent:main:session-1"

    def test_with_channel(self):
        key = build_explicit_session_id_session_key("main", "s1", channel="telegram")
        assert key == "agent:main:telegram:s1"

    def test_with_scope(self):
        key = build_explicit_session_id_session_key("main", "s1", channel="telegram", scope="group")
        assert key == "agent:main:telegram:group:s1"


class TestResolveSessionKey:
    def test_explicit_session_key(self):
        result = resolve_session_key_for_request({"sessionKey": "agent:main:s1"})
        assert result == "agent:main:s1"

    def test_from_session_id(self):
        result = resolve_session_key_for_request({"agentId": "main", "sessionId": "s1"})
        assert result == "agent:main:s1"

    def test_with_channel(self):
        result = resolve_session_key_for_request({
            "agentId": "main", "sessionId": "s1", "channel": "telegram",
        })
        assert result == "agent:main:telegram:s1"

    def test_no_session(self):
        assert resolve_session_key_for_request({}) is None

    def test_empty_session_key(self):
        assert resolve_session_key_for_request({"sessionKey": "  "}) is None
