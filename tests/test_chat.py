"""Tests for chat — tool content and canvas rendering."""

from __future__ import annotations

from openclaw.chat import (
    coerce_canvas_preview,
    extract_canvas_previews,
    is_tool_call_block,
    is_tool_call_content_type,
    is_tool_result_block,
    is_tool_result_content_type,
    resolve_tool_block_args,
    resolve_tool_use_id,
)


class TestToolContent:
    def test_is_tool_call_content_type(self):
        assert is_tool_call_content_type("toolcall") is True
        assert is_tool_call_content_type("tool_call") is True
        assert is_tool_call_content_type("tooluse") is True
        assert is_tool_call_content_type("tool_use") is True
        assert is_tool_call_content_type("text") is False

    def test_is_tool_result_content_type(self):
        assert is_tool_result_content_type("toolresult") is True
        assert is_tool_result_content_type("tool_result") is True
        assert is_tool_result_content_type("text") is False

    def test_is_tool_call_block(self):
        assert is_tool_call_block({"type": "tool_call"}) is True
        assert is_tool_call_block({"type": "text"}) is False

    def test_is_tool_result_block(self):
        assert is_tool_result_block({"type": "tool_result"}) is True
        assert is_tool_result_block({"type": "text"}) is False

    def test_resolve_args(self):
        assert resolve_tool_block_args({"args": {"x": 1}}) == {"x": 1}
        assert resolve_tool_block_args({"arguments": {"y": 2}}) == {"y": 2}
        assert resolve_tool_block_args({"input": "data"}) == "data"
        assert resolve_tool_block_args({}) is None

    def test_resolve_tool_use_id(self):
        assert resolve_tool_use_id({"id": "call-1"}) == "call-1"
        assert resolve_tool_use_id({"tool_call_id": "call-2"}) == "call-2"
        assert resolve_tool_use_id({"toolCallId": "call-3"}) == "call-3"
        assert resolve_tool_use_id({"tool_use_id": "call-4"}) == "call-4"
        assert resolve_tool_use_id({"toolUseId": "call-5"}) == "call-5"
        assert resolve_tool_use_id({}) is None
        assert resolve_tool_use_id({"id": ""}) is None


class TestCanvasRender:
    def test_coerce_valid_preview(self):
        record = {
            "kind": "canvas",
            "surface": "assistant_message",
            "url": "https://example.com/canvas",
            "title": "My Canvas",
        }
        preview = coerce_canvas_preview(record)
        assert preview is not None
        assert preview["kind"] == "canvas"
        assert preview["surface"] == "assistant_message"
        assert preview["url"] == "https://example.com/canvas"
        assert preview["title"] == "My Canvas"

    def test_coerce_invalid_kind(self):
        assert coerce_canvas_preview({"kind": "text"}) is None

    def test_coerce_invalid_surface(self):
        assert coerce_canvas_preview({"kind": "canvas", "surface": "sidebar"}) is None

    def test_coerce_none(self):
        assert coerce_canvas_preview(None) is None

    def test_extract_previews_from_shortcode(self):
        text = "Hello [canvas:url=https://example.com/c] world"
        result = extract_canvas_previews(text)
        assert len(result["previews"]) >= 1
        assert "Hello" in result["text"]
        assert "world" in result["text"]
        assert "[canvas" not in result["text"]

    def test_extract_no_previews(self):
        result = extract_canvas_previews("just plain text")
        assert result["previews"] == []
        assert result["text"] == "just plain text"
