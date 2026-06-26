"""Tests for infra/command-analysis policy module."""

from openclaw.infra.command_analysis.policy import (
    analyze_command_for_policy,
    detect_policy_inline_eval,
    detect_inline_eval_in_segments,
    ExecCommandSegment,
)


class TestAnalyzeCommandForPolicy:
    def test_valid_argv(self):
        result = analyze_command_for_policy({
            "source": "argv",
            "argv": ["ls", "-la", "/tmp"],
        })
        assert result["ok"] is True
        assert result["source"] == "argv"
        assert len(result["segments"]) == 3
        assert result["segments"][0].kind == "program"
        assert result["segments"][1].kind == "flag"
        assert result["segments"][2].kind == "arg"

    def test_empty_argv(self):
        result = analyze_command_for_policy({
            "source": "argv",
            "argv": [],
        })
        assert result["ok"] is False
        assert result["segments"] == []

    def test_single_program(self):
        result = analyze_command_for_policy({
            "source": "argv",
            "argv": ["echo"],
        })
        assert result["ok"] is True
        assert len(result["segments"]) == 1
        assert result["segments"][0].text == "echo"


class TestDetectInlineEval:
    def test_no_eval(self):
        segments = [ExecCommandSegment(text="ls"), ExecCommandSegment(text="-la")]
        result = detect_inline_eval_in_segments(segments)
        assert result["detected"] is False
        assert result["matches"] == []

    def test_command_substitution(self):
        segments = [ExecCommandSegment(text="$(rm -rf /)")]
        result = detect_inline_eval_in_segments(segments)
        assert result["detected"] is True

    def test_backtick_eval(self):
        segments = [ExecCommandSegment(text="`whoami`")]
        result = detect_inline_eval_in_segments(segments)
        assert result["detected"] is True

    def test_eval_keyword(self):
        segments = [ExecCommandSegment(text="eval"), ExecCommandSegment(text="dangerous")]
        result = detect_inline_eval_in_segments(segments)
        assert result["detected"] is True

    def test_exec_keyword(self):
        segments = [ExecCommandSegment(text="exec"), ExecCommandSegment(text="/bin/sh")]
        result = detect_inline_eval_in_segments(segments)
        assert result["detected"] is True

    def test_policy_alias(self):
        segments = [ExecCommandSegment(text="$(whoami)")]
        result = detect_policy_inline_eval(segments)
        assert result["detected"] is True
