"""Tests for trajectory and transcripts modules."""

import asyncio
import os

from openclaw.trajectory.paths import (
    TRAJECTORY_RUNTIME_CAPTURE_MAX_BYTES,
    TRAJECTORY_RUNTIME_FILE_MAX_BYTES,
    TRAJECTORY_RUNTIME_EVENT_MAX_BYTES,
    safe_trajectory_session_file_name,
    resolve_trajectory_file_path,
    resolve_trajectory_pointer_file_path,
)
from openclaw.transcripts.manual_source import (
    parse_speaker_line,
    manual_transcript_source_provider,
)


class TestTrajectoryPaths:
    def test_constants(self):
        assert TRAJECTORY_RUNTIME_CAPTURE_MAX_BYTES == 10 * 1024 * 1024
        assert TRAJECTORY_RUNTIME_FILE_MAX_BYTES == 50 * 1024 * 1024
        assert TRAJECTORY_RUNTIME_EVENT_MAX_BYTES == 256 * 1024

    def test_safe_session_file_name(self):
        assert safe_trajectory_session_file_name("sess-123") == "sess-123"
        assert safe_trajectory_session_file_name("a/b\\c") == "a_b_c"
        assert safe_trajectory_session_file_name("!!!") == "session"
        assert safe_trajectory_session_file_name("") == "session"
        assert safe_trajectory_session_file_name(123) == "session"

    def test_safe_truncates(self):
        long_id = "a" * 200
        result = safe_trajectory_session_file_name(long_id)
        assert len(result) <= 120

    def test_resolve_with_dir_override(self, tmp_path):
        result = resolve_trajectory_file_path({
            "sessionId": "sess-1",
            "env": {"OPENCLAW_TRAJECTORY_DIR": str(tmp_path)},
        })
        assert "sess-1.jsonl" in result
        assert str(tmp_path) in result

    def test_resolve_with_session_file_jsonl(self):
        result = resolve_trajectory_file_path({
            "sessionId": "s",
            "sessionFile": "/path/to/session.jsonl",
        })
        assert result == "/path/to/session.trajectory.jsonl"

    def test_resolve_with_session_file_other(self):
        result = resolve_trajectory_file_path({
            "sessionId": "s",
            "sessionFile": "/path/to/session.txt",
        })
        assert result == "/path/to/session.txt.trajectory.jsonl"

    def test_resolve_no_session_file(self):
        result = resolve_trajectory_file_path({"sessionId": "s", "env": {}})
        assert "s.trajectory.jsonl" in result

    def test_pointer_file_path_jsonl(self):
        assert resolve_trajectory_pointer_file_path("/p/s.jsonl") == "/p/s.trajectory-path.json"

    def test_pointer_file_path_other(self):
        assert resolve_trajectory_pointer_file_path("/p/s.txt") == "/p/s.txt.trajectory-path.json"


class TestParseSpeakerLine:
    def test_with_speaker(self):
        result = parse_speaker_line("Alice: Hello world")
        assert result["speaker_label"] == "Alice"
        assert result["text"] == "Hello world"

    def test_without_speaker(self):
        result = parse_speaker_line("Just text")
        assert result["speaker_label"] is None
        assert result["text"] == "Just text"

    def test_empty(self):
        result = parse_speaker_line("")
        assert result["text"] == ""

    def test_non_string(self):
        result = parse_speaker_line(123)
        assert result["text"] == ""


class TestManualTranscriptProvider:
    def test_provider_metadata(self):
        assert manual_transcript_source_provider["id"] == "manual-transcript"
        assert "import" in manual_transcript_source_provider["aliases"]

    def test_import_simple(self):
        request = {
            "text": "Hello world",
            "session": {"sessionId": "s1"},
        }
        result = asyncio.run(manual_transcript_source_provider["importTranscript"](request))
        assert len(result) == 1
        assert result[0]["text"] == "Hello world"
        assert result[0]["speaker"]["label"] == "Speaker"

    def test_import_with_speaker_labels(self):
        request = {
            "text": "Alice: Hi\nBob: Hello",
            "session": {"sessionId": "s1"},
        }
        result = asyncio.run(manual_transcript_source_provider["importTranscript"](request))
        assert len(result) == 2
        assert result[0]["speaker"]["label"] == "Alice"
        assert result[1]["speaker"]["label"] == "Bob"

    def test_import_skips_empty_lines(self):
        request = {
            "text": "Line 1\n\n\nLine 2",
            "session": {"sessionId": "s1"},
        }
        result = asyncio.run(manual_transcript_source_provider["importTranscript"](request))
        assert len(result) == 2

    def test_import_with_custom_speaker(self):
        request = {
            "text": "Just text",
            "session": {"sessionId": "s1"},
            "speakerLabel": "User",
        }
        result = asyncio.run(manual_transcript_source_provider["importTranscript"](request))
        assert result[0]["speaker"]["label"] == "User"

    def test_import_ids_increment(self):
        request = {
            "text": "A\nB\nC",
            "session": {"sessionId": "sess"},
        }
        result = asyncio.run(manual_transcript_source_provider["importTranscript"](request))
        assert result[0]["id"] == "sess-1"
        assert result[1]["id"] == "sess-2"
        assert result[2]["id"] == "sess-3"
