"""Tests for shared root modules."""

from openclaw.shared.regexp import escape_regexp
from openclaw.shared.account_enabled import is_account_enabled
from openclaw.shared.human_list import format_human_list
from openclaw.shared.agent_run_status import (
    is_non_terminal_agent_run_status,
    NON_TERMINAL_AGENT_RUN_STATUSES,
)


class TestEscapeRegexp:
    def test_dots(self):
        assert escape_regexp("a.b") == "a\\.b"

    def test_special_chars(self):
        result = escape_regexp("a*b+c?d")
        assert "\\" in result

    def test_empty(self):
        assert escape_regexp("") == ""

    def test_non_string(self):
        assert escape_regexp(123) == ""


class TestIsAccountEnabled:
    def test_enabled_true(self):
        assert is_account_enabled({"enabled": True}) is True

    def test_enabled_false(self):
        assert is_account_enabled({"enabled": False}) is False

    def test_no_enabled_key(self):
        assert is_account_enabled({"name": "x"}) is True

    def test_non_object(self):
        assert is_account_enabled(None) is True
        assert is_account_enabled("string") is True
        assert is_account_enabled(123) is True


class TestFormatHumanList:
    def test_empty(self):
        assert format_human_list([]) == ""

    def test_single(self):
        assert format_human_list(["A"]) == "A"

    def test_two(self):
        assert format_human_list(["A", "B"]) == "A or B"

    def test_three(self):
        assert format_human_list(["A", "B", "C"]) == "A, B, or C"

    def test_four(self):
        assert format_human_list(["A", "B", "C", "D"]) == "A, B, C, or D"


class TestAgentRunStatus:
    def test_non_terminal(self):
        assert is_non_terminal_agent_run_status("accepted") is True
        assert is_non_terminal_agent_run_status("started") is True
        assert is_non_terminal_agent_run_status("in_flight") is True

    def test_terminal(self):
        assert is_non_terminal_agent_run_status("completed") is False
        assert is_non_terminal_agent_run_status("failed") is False
        assert is_non_terminal_agent_run_status("") is False

    def test_non_string(self):
        assert is_non_terminal_agent_run_status(None) is False
        assert is_non_terminal_agent_run_status(123) is False
