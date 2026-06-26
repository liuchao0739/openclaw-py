"""Tests for config/sessions — version, transcript header, maintenance."""

from __future__ import annotations

from openclaw.config.sessions import (
    CURRENT_SESSION_VERSION,
    create_session_transcript_header,
    resolve_maintenance_config,
)


class TestVersion:
    def test_current_version(self):
        assert CURRENT_SESSION_VERSION == 3


class TestTranscriptHeader:
    def test_basic(self):
        header = create_session_transcript_header()
        assert header["type"] == "session"
        assert header["version"] == 3
        assert "id" in header
        assert "timestamp" in header
        assert "cwd" in header

    def test_with_session_id(self):
        header = create_session_transcript_header(session_id="my-session")
        assert header["id"] == "my-session"

    def test_with_cwd(self):
        header = create_session_transcript_header(cwd="/custom/path")
        assert header["cwd"] == "/custom/path"

    def test_generates_uuid(self):
        header1 = create_session_transcript_header()
        header2 = create_session_transcript_header()
        assert header1["id"] != header2["id"]


class TestResolveMaintenanceConfig:
    def test_defaults(self):
        config = resolve_maintenance_config()
        assert config["enabled"] is False
        assert config["maxAgeHours"] == 168
        assert config["maxEntries"] == 1000
