"""Tests for gateway/test session helpers."""

import json

from openclaw.gateway.test.server_sessions_test_helpers import (
    create_linear_session_transcript,
    create_deferred,
    session_store_entry,
    is_internal_hook_event,
)


class TestCreateLinearSessionTranscript:
    def test_empty_contents(self):
        transcript = create_linear_session_transcript("sess-1", [])
        lines = transcript.strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["type"] == "session"
        assert record["id"] == "sess-1"

    def test_with_messages(self):
        transcript = create_linear_session_transcript("sess-1", ["hello", "world"])
        lines = transcript.strip().split("\n")
        assert len(lines) == 3
        msg1 = json.loads(lines[1])
        assert msg1["type"] == "message"
        assert msg1["message"]["content"] == "hello"
        assert msg1["parentId"] is None
        msg2 = json.loads(lines[2])
        assert msg2["message"]["content"] == "world"
        assert msg2["parentId"] == "sess-1-entry-0"

    def test_ends_with_newline(self):
        transcript = create_linear_session_transcript("s", ["a"])
        assert transcript.endswith("\n")


class TestCreateDeferred:
    def test_resolve(self):
        d = create_deferred()
        assert not d.resolved
        d.resolve(42)
        assert d.resolved

    def test_reject(self):
        d = create_deferred()
        assert not d.rejected
        d.reject("error")
        assert d.rejected

    def test_resolve_once(self):
        d = create_deferred()
        d.resolve(1)
        d.resolve(2)
        assert d._value == 1


class TestSessionStoreEntry:
    def test_basic(self):
        entry = session_store_entry("sess-1")
        assert entry["sessionId"] == "sess-1"
        assert "updatedAt" in entry

    def test_with_overrides(self):
        entry = session_store_entry("sess-1", {"sessionFile": "/path/to/file"})
        assert entry["sessionFile"] == "/path/to/file"
        assert entry["sessionId"] == "sess-1"


class TestIsInternalHookEvent:
    def test_valid_event(self):
        event = {
            "type": "session",
            "action": "end",
            "sessionKey": "agent:main:sess-1",
            "messages": [],
            "context": {"key": "value"},
        }
        assert is_internal_hook_event(event) is True

    def test_missing_type(self):
        event = {"action": "end", "sessionKey": "k", "messages": [], "context": {}}
        assert is_internal_hook_event(event) is False

    def test_non_dict(self):
        assert is_internal_hook_event(None) is False
        assert is_internal_hook_event("string") is False

    def test_messages_not_list(self):
        event = {
            "type": "s",
            "action": "a",
            "sessionKey": "k",
            "messages": "not a list",
            "context": {},
        }
        assert is_internal_hook_event(event) is False

    def test_context_not_dict(self):
        event = {
            "type": "s",
            "action": "a",
            "sessionKey": "k",
            "messages": [],
            "context": "not a dict",
        }
        assert is_internal_hook_event(event) is False
