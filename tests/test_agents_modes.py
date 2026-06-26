"""Tests for agents/modes interactive components."""

from openclaw.agents.modes.interactive.components.visual_truncate import (
    truncate_to_visual_lines,
    VisualTruncateResult,
)


class TestTruncateToVisualLines:
    def test_empty(self):
        result = truncate_to_visual_lines("", 10, 80)
        assert result.visual_lines == []
        assert result.skipped_count == 0

    def test_short_text(self):
        result = truncate_to_visual_lines("hello", 10, 80)
        assert result.visual_lines == ["hello"]
        assert result.skipped_count == 0

    def test_truncate_from_end(self):
        text = "\n".join(f"line{i}" for i in range(20))
        result = truncate_to_visual_lines(text, 5, 80)
        assert len(result.visual_lines) == 5
        assert result.visual_lines[0] == "line15"
        assert result.skipped_count == 15

    def test_wrapping(self):
        text = "a" * 200
        result = truncate_to_visual_lines(text, 3, 50)
        assert len(result.visual_lines) == 3
        assert result.skipped_count > 0

    def test_padding(self):
        text = "a" * 100
        result = truncate_to_visual_lines(text, 100, 50, padding_x=5)
        # effective width = 50 - 10 = 40
        expected_lines = (100 + 39) // 40
        assert len(result.visual_lines) == expected_lines

    def test_exact_fit(self):
        text = "\n".join(["a"] * 5)
        result = truncate_to_visual_lines(text, 5, 80)
        assert len(result.visual_lines) == 5
        assert result.skipped_count == 0

    def test_result_type(self):
        result = truncate_to_visual_lines("hi", 10, 80)
        assert isinstance(result, VisualTruncateResult)
