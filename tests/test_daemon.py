"""Tests for daemon core modules."""

import io
import os

import pytest

from openclaw.daemon.container_context import resolve_daemon_container_context
from openclaw.daemon.runtime_parse import parse_key_value_output
from openclaw.daemon.output import to_posix_path, format_line, write_formatted_lines


class TestContainerContext:
    def test_hint_present(self):
        assert resolve_daemon_container_context({"OPENCLAW_CONTAINER_HINT": "docker"}) == "docker"

    def test_fallback_to_container(self):
        assert resolve_daemon_container_context({"OPENCLAW_CONTAINER": "k8s"}) == "k8s"

    def test_hint_takes_precedence(self):
        env = {"OPENCLAW_CONTAINER_HINT": "docker", "OPENCLAW_CONTAINER": "k8s"}
        assert resolve_daemon_container_context(env) == "docker"

    def test_none_when_absent(self):
        assert resolve_daemon_container_context({}) is None

    def test_whitespace_normalized(self):
        assert resolve_daemon_container_context({"OPENCLAW_CONTAINER_HINT": "  docker  "}) == "docker"

    def test_empty_string_none(self):
        assert resolve_daemon_container_context({"OPENCLAW_CONTAINER_HINT": "  "}) is None


class TestRuntimeParse:
    def test_basic_colon_separator(self):
        output = "name: my-service\nstatus: running"
        result = parse_key_value_output(output, ":")
        assert result == {"name": "my-service", "status": "running"}

    def test_equals_separator(self):
        output = "KEY1=val1\nKEY2=val2"
        result = parse_key_value_output(output, "=")
        assert result == {"key1": "val1", "key2": "val2"}

    def test_skips_blank_lines(self):
        output = "a: 1\n\n\nb: 2"
        result = parse_key_value_output(output, ":")
        assert result == {"a": "1", "b": "2"}

    def test_skips_no_separator(self):
        output = "nokey\na: 1"
        result = parse_key_value_output(output, ":")
        assert result == {"a": "1"}

    def test_keys_lowercased(self):
        result = parse_key_value_output("NAME: x", ":")
        assert "name" in result

    def test_value_trimmed(self):
        result = parse_key_value_output("a:   hello world   ", ":")
        assert result["a"] == "hello world"

    def test_crlf_lines(self):
        result = parse_key_value_output("a: 1\r\nb: 2", ":")
        assert result == {"a": "1", "b": "2"}

    def test_empty_output(self):
        assert parse_key_value_output("", ":") == {}

    def test_separator_at_start_skipped(self):
        assert parse_key_value_output(": value", ":") == {}


class TestOutput:
    def test_to_posix_path(self):
        assert to_posix_path(r"C:\Users\test") == "C:/Users/test"

    def test_to_posix_already_posix(self):
        assert to_posix_path("/usr/local/bin") == "/usr/local/bin"

    def test_format_line(self):
        assert format_line("Status", "running") == "Status: running"

    def test_write_formatted_lines(self):
        buf = io.StringIO()
        write_formatted_lines(buf, [{"label": "A", "value": "1"}, {"label": "B", "value": "2"}])
        assert buf.getvalue() == "A: 1\nB: 2\n"

    def test_write_with_leading_blank(self):
        buf = io.StringIO()
        write_formatted_lines(buf, [{"label": "A", "value": "1"}], {"leadingBlankLine": True})
        assert buf.getvalue() == "\nA: 1\n"

    def test_write_empty(self):
        buf = io.StringIO()
        write_formatted_lines(buf, [])
        assert buf.getvalue() == ""
