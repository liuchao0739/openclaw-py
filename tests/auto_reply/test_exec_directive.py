"""Tests for auto_reply/reply/exec — directive parsing."""

from __future__ import annotations

import pytest

from openclaw.auto_reply.reply.exec.directive import extract_exec_directive


class TestExtractExecDirective:
    def test_no_directive(self):
        result = extract_exec_directive("hello world")
        assert result["hasDirective"] is False
        assert result["cleaned"] == "hello world"

    def test_empty_body(self):
        result = extract_exec_directive(None)
        assert result["hasDirective"] is False
        assert result["cleaned"] == ""

    def test_exec_host(self):
        result = extract_exec_directive("hello /exec host=local world")
        assert result["hasDirective"] is True
        assert result["execHost"] == "local"
        assert result["invalidHost"] is False
        assert "hello" in result["cleaned"]
        assert "world" in result["cleaned"]
        assert "/exec" not in result["cleaned"]

    def test_exec_host_colon_syntax(self):
        result = extract_exec_directive("/exec host:remote do something")
        assert result["execHost"] == "remote"

    def test_exec_security(self):
        result = extract_exec_directive("/exec security=full task")
        assert result["execSecurity"] == "full"
        assert result["invalidSecurity"] is False

    def test_exec_ask(self):
        result = extract_exec_directive("/exec ask=always task")
        assert result["execAsk"] == "always"

    def test_exec_node(self):
        result = extract_exec_directive("/exec node=node-1 task")
        assert result["execNode"] == "node-1"

    def test_multiple_options(self):
        result = extract_exec_directive("/exec host=local security=full ask=off task")
        assert result["execHost"] == "local"
        assert result["execSecurity"] == "full"
        assert result["execAsk"] == "off"
        assert result["hasExecOptions"] is True

    def test_invalid_host(self):
        result = extract_exec_directive("/exec host=invalid task")
        assert result["invalidHost"] is True
        assert result["execHost"] is None

    def test_invalid_security(self):
        result = extract_exec_directive("/exec security=bogus task")
        assert result["invalidSecurity"] is True

    def test_invalid_ask(self):
        result = extract_exec_directive("/exec ask=bogus task")
        assert result["invalidAsk"] is True

    def test_invalid_node_empty(self):
        result = extract_exec_directive("/exec node= task")
        assert result["invalidNode"] is True

    def test_directive_at_start(self):
        result = extract_exec_directive("/exec host=local do task")
        assert result["hasDirective"] is True
        assert result["execHost"] == "local"
        assert "do task" in result["cleaned"]

    def test_directive_in_middle(self):
        result = extract_exec_directive("hello /exec host=sandbox world")
        assert result["hasDirective"] is True
        assert result["execHost"] == "sandbox"
        assert "hello" in result["cleaned"]
        assert "world" in result["cleaned"]

    def test_no_options(self):
        result = extract_exec_directive("/exec task without options")
        assert result["hasDirective"] is True
        assert result["hasExecOptions"] is False

    def test_preserves_remaining_text(self):
        result = extract_exec_directive("hello /exec host=local this is my prompt")
        assert "this is my prompt" in result["cleaned"]
        assert "hello" in result["cleaned"]
