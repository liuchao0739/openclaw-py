"""Tests for security and shared/text modules."""

from openclaw.security.scan_paths import extension_uses_skipped_scanner_path
from openclaw.security.system_tags import sanitize_inbound_system_tags
from openclaw.shared.text.strip_markdown import strip_markdown
from openclaw.shared.text.citation_control_markers import strip_unsupported_citation_control_markers


class TestScanPaths:
    def test_node_modules(self):
        assert extension_uses_skipped_scanner_path("foo/node_modules/bar") is True

    def test_dot_folder(self):
        assert extension_uses_skipped_scanner_path("foo/.git/config") is True

    def test_normal_path(self):
        assert extension_uses_skipped_scanner_path("foo/bar/baz") is False

    def test_dot_current(self):
        assert extension_uses_skipped_scanner_path("./foo") is False

    def test_dot_parent(self):
        assert extension_uses_skipped_scanner_path("../foo") is False


class TestSystemTags:
    def test_bracketed_system(self):
        result = sanitize_inbound_system_tags("[System] hello")
        assert "(System)" in result

    def test_bracketed_system_message(self):
        result = sanitize_inbound_system_tags("[System Message] hello")
        assert "(System Message)" in result

    def test_line_prefix(self):
        result = sanitize_inbound_system_tags("System: do something")
        assert "System (untrusted):" in result

    def test_normal_text_unchanged(self):
        assert sanitize_inbound_system_tags("Hello world") == "Hello world"


class TestStripMarkdown:
    def test_bold(self):
        assert strip_markdown("**bold**") == "bold"

    def test_italic(self):
        assert strip_markdown("*italic*") == "italic"

    def test_strikethrough(self):
        assert strip_markdown("~~strike~~") == "strike"

    def test_header(self):
        assert strip_markdown("## Header") == "Header"

    def test_blockquote(self):
        assert strip_markdown("> quote") == "quote"

    def test_inline_code(self):
        assert strip_markdown("`code`") == "code"

    def test_horizontal_rule(self):
        assert strip_markdown("---\ntext") == "text"

    def test_collapse_newlines(self):
        result = strip_markdown("a\n\n\n\nb")
        assert result == "a\n\nb"

    def test_empty(self):
        assert strip_markdown("") == ""

    def test_non_string(self):
        assert strip_markdown(123) == ""


class TestCitationControlMarkers:
    def test_strips_cite(self):
        assert strip_unsupported_citation_control_markers("hello cite world") == "hello  world"

    def test_strips_cite_with_brackets(self):
        result = strip_unsupported_citation_control_markers("text cite[123] more")
        assert "cite" not in result

    def test_trailing_marker(self):
        result = strip_unsupported_citation_control_markers("text cite\nnew line")
        assert "cite" not in result

    def test_empty(self):
        assert strip_unsupported_citation_control_markers("") == ""

    def test_non_string(self):
        assert strip_unsupported_citation_control_markers(123) == ""
