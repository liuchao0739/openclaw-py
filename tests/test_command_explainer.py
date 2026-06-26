"""Tests for infra/command-explainer format module."""

from openclaw.infra.command_explainer.format import (
    span_to_command_span,
    format_command_spans,
)


class TestSpanToCommandSpan:
    def test_valid_span(self):
        assert span_to_command_span({"startIndex": 0, "endIndex": 5}) == {
            "startIndex": 0,
            "endIndex": 5,
        }

    def test_negative_start(self):
        assert span_to_command_span({"startIndex": -1, "endIndex": 5}) is None

    def test_end_before_start(self):
        assert span_to_command_span({"startIndex": 5, "endIndex": 3}) is None

    def test_end_equals_start(self):
        assert span_to_command_span({"startIndex": 3, "endIndex": 3}) is None

    def test_non_integer(self):
        assert span_to_command_span({"startIndex": "0", "endIndex": 5}) is None
        assert span_to_command_span({"startIndex": 0, "endIndex": "5"}) is None

    def test_boolean_rejected(self):
        assert span_to_command_span({"startIndex": True, "endIndex": 5}) is None


class TestFormatCommandSpans:
    def test_empty_explanation(self):
        assert format_command_spans({}) == []

    def test_valid_commands(self):
        explanation = {
            "topLevelCommands": [
                {"argv": ["ls"], "executableSpan": {"startIndex": 0, "endIndex": 2}},
            ],
            "nestedCommands": [],
        }
        spans = format_command_spans(explanation)
        assert len(spans) == 1
        assert spans[0] == {"startIndex": 0, "endIndex": 2}

    def test_nested_commands(self):
        explanation = {
            "topLevelCommands": [
                {"argv": ["ls"], "executableSpan": {"startIndex": 0, "endIndex": 2}},
            ],
            "nestedCommands": [
                {"argv": ["grep"], "executableSpan": {"startIndex": 5, "endIndex": 9}},
            ],
        }
        spans = format_command_spans(explanation)
        assert len(spans) == 2

    def test_unsupported_shell_returns_empty(self):
        explanation = {
            "topLevelCommands": [
                {"argv": ["fish", "-c", "echo"], "executableSpan": {"startIndex": 0, "endIndex": 4}},
            ],
            "nestedCommands": [],
        }
        assert format_command_spans(explanation) == []

    def test_invalid_span_skipped(self):
        explanation = {
            "topLevelCommands": [
                {"argv": ["ls"], "executableSpan": {"startIndex": -1, "endIndex": 2}},
                {"argv": ["grep"], "executableSpan": {"startIndex": 5, "endIndex": 9}},
            ],
            "nestedCommands": [],
        }
        spans = format_command_spans(explanation)
        assert len(spans) == 1
        assert spans[0]["startIndex"] == 5

    def test_full_path_executable(self):
        explanation = {
            "topLevelCommands": [
                {"argv": ["/usr/bin/bash", "-c", "ls"], "executableSpan": {"startIndex": 0, "endIndex": 4}},
            ],
            "nestedCommands": [],
        }
        spans = format_command_spans(explanation)
        assert len(spans) == 1  # bash is supported
