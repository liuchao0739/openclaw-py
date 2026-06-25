"""Tests for agents/sessions/tools — truncate, limits, path-utils, edit-diff, render-utils."""

from __future__ import annotations

import os

import pytest

from openclaw.agents.sessions.tools.edit_diff import (
    apply_edits_to_normalized_content,
    detect_line_ending,
    generate_unified_patch,
    normalize_to_lf,
    strip_bom,
)
from openclaw.agents.sessions.tools.file_mutation_queue import with_file_mutation_queue
from openclaw.agents.sessions.tools.limits import (
    SESSION_TOOL_STDERR_TAIL_BYTES,
    append_bounded_text_tail,
    normalize_positive_limit,
)
from openclaw.agents.sessions.tools.path_utils import resolve_to_cwd
from openclaw.agents.sessions.tools.render_utils import (
    get_text_output,
    normalize_display_text,
    replace_tabs,
    shorten_path,
    str_value,
    strip_ansi,
)
from openclaw.agents.sessions.tools.tool_definition_wrapper import (
    create_tool_definition_from_agent_tool,
    wrap_tool_definition,
)
from openclaw.agents.sessions.tools.truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    format_size,
    truncate_head,
    truncate_line,
    truncate_tail,
)


class TestTruncate:
    def test_truncate_line_short(self):
        assert truncate_line("hello", 10) == "hello"

    def test_truncate_line_long(self):
        result = truncate_line("a" * 100, 10)
        assert len(result) == 13  # 10 + "..."
        assert result.endswith("...")

    def test_truncate_tail_no_truncation(self):
        result = truncate_tail("hello\nworld")
        assert result["truncated"] is False
        assert result["content"] == "hello\nworld"

    def test_truncate_tail_with_limits(self):
        text = "\n".join(str(i) for i in range(100))
        result = truncate_tail(text, {"maxLines": 5})
        assert result["truncated"] is True
        assert result["truncatedBy"] == "lines"
        lines = result["content"].split("\n")
        assert len(lines) <= 5

    def test_truncate_head_keeps_beginning(self):
        text = "\n".join(str(i) for i in range(100))
        result = truncate_head(text, {"maxLines": 5})
        assert result["truncated"] is True
        lines = result["content"].split("\n")
        assert lines[0] == "0"

    def test_format_size(self):
        assert format_size(500) == "500B"
        assert "KB" in format_size(2048)
        assert "MB" in format_size(2 * 1024 * 1024)


class TestLimits:
    def test_normalize_positive_limit(self):
        assert normalize_positive_limit(10, 5) == 10
        assert normalize_positive_limit(None, 5) == 5
        assert normalize_positive_limit(float("inf"), 5) == 5
        assert normalize_positive_limit(0, 5) == 1  # max(1, 0) = 1
        assert normalize_positive_limit(3.7, 5) == 3

    def test_append_bounded_text_tail_under_limit(self):
        result = append_bounded_text_tail("hello", " world", 100)
        assert result == "hello world"

    def test_append_bounded_text_tail_truncates(self):
        large = "x" * 200
        result = append_bounded_text_tail("existing", large, 50)
        assert len(result.encode("utf-8")) <= 50


class TestPathUtils:
    def test_resolve_to_cwd_absolute(self):
        assert resolve_to_cwd("/usr/bin/file", "/home") == "/usr/bin/file"

    def test_resolve_to_cwd_relative(self):
        result = resolve_to_cwd("file.txt", "/home")
        assert result == os.path.abspath(os.path.join("/home", "file.txt"))

    def test_resolve_to_cwd_home(self):
        result = resolve_to_cwd("~/file", "/home")
        assert result == os.path.expanduser("~") + "/file"

    def test_resolve_to_cwd_at_prefix(self):
        result = resolve_to_cwd("@file.txt", "/home")
        assert result == os.path.abspath(os.path.join("/home", "file.txt"))


class TestEditDiff:
    def test_detect_line_ending_lf(self):
        assert detect_line_ending("hello\nworld") == "\n"

    def test_detect_line_ending_crlf(self):
        assert detect_line_ending("hello\r\nworld") == "\r\n"

    def test_detect_line_ending_none(self):
        assert detect_line_ending("hello") == "\n"

    def test_normalize_to_lf(self):
        assert normalize_to_lf("hello\r\nworld\rtest") == "hello\nworld\ntest"

    def test_strip_bom(self):
        result = strip_bom("\uFEFFhello")
        assert result["bom"] == "\uFEFF"
        assert result["text"] == "hello"

    def test_strip_bom_no_bom(self):
        result = strip_bom("hello")
        assert result["bom"] == ""
        assert result["text"] == "hello"

    def test_apply_edits_simple(self):
        content = "hello world"
        edits = [{"oldText": "hello", "newText": "goodbye"}]
        result = apply_edits_to_normalized_content(content, edits, "test.txt")
        assert result["newContent"] == "goodbye world"

    def test_apply_edits_multiple(self):
        content = "aaa bbb ccc"
        edits = [
            {"oldText": "aaa", "newText": "AAA"},
            {"oldText": "ccc", "newText": "CCC"},
        ]
        result = apply_edits_to_normalized_content(content, edits, "test.txt")
        assert result["newContent"] == "AAA bbb CCC"

    def test_apply_edits_not_found(self):
        with pytest.raises(ValueError, match="Could not find"):
            apply_edits_to_normalized_content("hello", [{"oldText": "xyz", "newText": "abc"}], "test.txt")

    def test_apply_edits_empty_old_text(self):
        with pytest.raises(ValueError, match="must not be empty"):
            apply_edits_to_normalized_content("hello", [{"oldText": "", "newText": "abc"}], "test.txt")

    def test_apply_edits_duplicate(self):
        content = "hello hello"
        with pytest.raises(ValueError, match="occurrences"):
            apply_edits_to_normalized_content(content, [{"oldText": "hello", "newText": "hi"}], "test.txt")

    def test_apply_edits_overlap(self):
        content = "abcdef"
        edits = [
            {"oldText": "abc", "newText": "ABC"},
            {"oldText": "cde", "newText": "CDE"},
        ]
        with pytest.raises(ValueError, match="overlap"):
            apply_edits_to_normalized_content(content, edits, "test.txt")

    def test_apply_edits_no_change(self):
        with pytest.raises(ValueError, match="No changes"):
            apply_edits_to_normalized_content("hello", [{"oldText": "hello", "newText": "hello"}], "test.txt")

    def test_generate_unified_patch(self):
        patch = generate_unified_patch("test.txt", "hello\n", "goodbye\n")
        assert "---" in patch
        assert "+++" in patch
        assert "-hello" in patch
        assert "+goodbye" in patch


class TestRenderUtils:
    def test_shorten_path(self):
        home = os.path.expanduser("~")
        assert shorten_path(f"{home}/projects/file.txt") == "~/projects/file.txt"

    def test_shorten_path_non_string(self):
        assert shorten_path(None) == ""
        assert shorten_path(123) == ""

    def test_str_value(self):
        assert str_value("hello") == "hello"
        assert str_value(None) == ""
        assert str_value(123) is None

    def test_replace_tabs(self):
        assert replace_tabs("a\tb") == "a   b"

    def test_normalize_display_text(self):
        assert normalize_display_text("hello\r\nworld\r") == "hello\nworld"

    def test_strip_ansi(self):
        assert strip_ansi("\x1b[31mred\x1b[0m text") == "red text"

    def test_get_text_output_none(self):
        assert get_text_output(None) == ""

    def test_get_text_output_text_blocks(self):
        result = {"content": [{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}]}
        assert get_text_output(result) == "hello\nworld"


class TestFileMutationQueue:
    async def test_serializes_same_file(self):
        order: list[str] = []

        async def op1():
            order.append("op1_start")
            await __import__("asyncio").sleep(0.01)
            order.append("op1_end")

        async def op2():
            order.append("op2_start")
            order.append("op2_end")

        await with_file_mutation_queue("/tmp/test_file.txt", op1)
        await with_file_mutation_queue("/tmp/test_file.txt", op2)
        assert order == ["op1_start", "op1_end", "op2_start", "op2_end"]


class TestToolDefinitionWrapper:
    def test_wrap_tool_definition(self):
        async def execute(tool_call_id, params, signal, on_update, ctx):
            return {"content": [], "ctx": ctx}

        definition = {"name": "my_tool", "label": "My", "description": "test", "execute": execute}
        tool = wrap_tool_definition(definition, lambda: {"id": "ctx1"})
        assert tool["name"] == "my_tool"
        assert tool["label"] == "My"

    def test_create_tool_definition_from_agent_tool(self):
        async def execute(tool_call_id, params, signal, on_update):
            return {"content": []}

        agent_tool = {"name": "test", "label": "Test", "description": "desc", "execute": execute}
        definition = create_tool_definition_from_agent_tool(agent_tool)
        assert definition["name"] == "test"
        assert definition["description"] == "desc"
