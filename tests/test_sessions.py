"""Tests for sessions modules."""

from openclaw.sessions.session_id import looks_like_session_id, SESSION_ID_RE
from openclaw.sessions.session_label import parse_session_label, SESSION_LABEL_MAX_LENGTH
from openclaw.sessions.classify_session_kind import classify_session_kind


class TestLooksLikeSessionId:
    def test_valid_uuid(self):
        assert looks_like_session_id("550e8400-e29b-41d4-a716-446655440000") is True

    def test_uppercase(self):
        assert looks_like_session_id("550E8400-E29B-41D4-A716-446655440000") is True

    def test_with_spaces(self):
        assert looks_like_session_id("  550e8400-e29b-41d4-a716-446655440000  ") is True

    def test_invalid(self):
        assert looks_like_session_id("not-a-uuid") is False
        assert looks_like_session_id("") is False
        assert looks_like_session_id("550e8400-e29b-41d4") is False

    def test_non_string(self):
        assert looks_like_session_id(123) is False
        assert looks_like_session_id(None) is False


class TestParseSessionLabel:
    def test_valid(self):
        result = parse_session_label("My Session")
        assert result["ok"] is True
        assert result["label"] == "My Session"

    def test_trims(self):
        result = parse_session_label("  trimmed  ")
        assert result["label"] == "trimmed"

    def test_non_string(self):
        result = parse_session_label(123)
        assert result["ok"] is False
        assert "string" in result["error"]

    def test_empty(self):
        result = parse_session_label("")
        assert result["ok"] is False
        assert "empty" in result["error"]

    def test_whitespace_only(self):
        result = parse_session_label("   ")
        assert result["ok"] is False

    def test_too_long(self):
        result = parse_session_label("x" * (SESSION_LABEL_MAX_LENGTH + 1))
        assert result["ok"] is False
        assert "too long" in result["error"]

    def test_exact_max_length(self):
        result = parse_session_label("x" * SESSION_LABEL_MAX_LENGTH)
        assert result["ok"] is True


class TestClassifySessionKind:
    def test_global(self):
        assert classify_session_kind("global") == "global"

    def test_unknown(self):
        assert classify_session_kind("unknown") == "unknown"

    def test_cron(self):
        assert classify_session_kind("cron:job-1") == "cron"
        assert classify_session_kind("agent:main:cron:job-1") == "cron"

    def test_spawn_child(self):
        assert classify_session_kind("some-key", {"spawnedBy": "parent"}) == "spawn-child"

    def test_group_chat_type(self):
        assert classify_session_kind("key", {"chatType": "group"}) == "group"
        assert classify_session_kind("key", {"chatType": "channel"}) == "group"

    def test_group_key_shape(self):
        assert classify_session_kind("agent:main:group:123") == "group"
        assert classify_session_kind("agent:main:channel:456") == "group"

    def test_direct_fallback(self):
        assert classify_session_kind("agent:main:sess-1") == "direct"

    def test_no_entry(self):
        assert classify_session_kind("agent:main:sess-1", None) == "direct"

    def test_spawn_before_key_shape(self):
        # spawn-child takes priority over group key shape
        assert classify_session_kind("agent:main:group:123", {"spawnedBy": "p"}) == "spawn-child"
