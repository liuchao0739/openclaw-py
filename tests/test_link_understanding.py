"""Tests for link-understanding modules."""

from openclaw.link_understanding.defaults import (
    DEFAULT_LINK_TIMEOUT_SECONDS,
    DEFAULT_MAX_LINKS,
)
from openclaw.link_understanding.format import format_link_understanding_body
from openclaw.link_understanding.detect import extract_links_from_message


class TestDefaults:
    def test_constants(self):
        assert DEFAULT_LINK_TIMEOUT_SECONDS == 30
        assert DEFAULT_MAX_LINKS == 3


class TestFormatLinkUnderstandingBody:
    def test_no_outputs(self):
        assert format_link_understanding_body({"body": "hello", "outputs": []}) == "hello"

    def test_no_body(self):
        result = format_link_understanding_body({"outputs": ["link1", "link2"]})
        assert result == "link1\nlink2"

    def test_with_body(self):
        result = format_link_understanding_body({"body": "msg", "outputs": ["summary"]})
        assert result == "msg\n\nsummary"

    def test_filters_empty_outputs(self):
        result = format_link_understanding_body({"body": "x", "outputs": ["", "  ", "valid"]})
        assert "valid" in result
        assert result == "x\n\nvalid"

    def test_none_body(self):
        result = format_link_understanding_body({"outputs": ["a"]})
        assert result == "a"


class TestExtractLinksFromMessage:
    def test_basic_url(self):
        result = extract_links_from_message("Check https://example.com out")
        assert result == ["https://example.com"]

    def test_multiple_urls(self):
        result = extract_links_from_message("See https://a.com and https://b.com")
        assert len(result) == 2

    def test_dedup(self):
        result = extract_links_from_message("https://a.com https://a.com")
        assert len(result) == 1

    def test_max_links(self):
        result = extract_links_from_message(
            "https://a.com https://b.com https://c.com https://d.com",
            {"maxLinks": 2},
        )
        assert len(result) == 2

    def test_localhost_blocked(self):
        result = extract_links_from_message("Check https://localhost:8080")
        assert result == []

    def test_private_ip_blocked(self):
        result = extract_links_from_message("Check https://10.0.0.1")
        assert result == []

    def test_markdown_links_ignored(self):
        result = extract_links_from_message("[text](https://example.com)")
        assert result == []

    def test_http_and_https(self):
        result = extract_links_from_message("http://a.com https://b.com")
        assert len(result) == 2

    def test_empty_message(self):
        assert extract_links_from_message("") == []
        assert extract_links_from_message("   ") == []

    def test_non_string(self):
        assert extract_links_from_message(123) == []

    def test_no_urls(self):
        assert extract_links_from_message("just text") == []

    def test_default_max_links(self):
        result = extract_links_from_message(
            "https://a.com https://b.com https://c.com https://d.com"
        )
        assert len(result) == DEFAULT_MAX_LINKS
