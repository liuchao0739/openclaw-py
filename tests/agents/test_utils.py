"""Tests for agents/utils — ansi, mime, paths, frontmatter, html, git, sleep, syntax-highlight."""

from __future__ import annotations

import asyncio

import pytest

from openclaw.agents.utils.ansi import strip_ansi
from openclaw.agents.utils.frontmatter import parse_frontmatter, strip_frontmatter
from openclaw.agents.utils.git import parse_git_url
from openclaw.agents.utils.html import decode_html_entities, decode_html_entity_at
from openclaw.agents.utils.mime import detect_supported_image_mime_type
from openclaw.agents.utils.paths import (
    canonicalize_path,
    format_path_relative_to_cwd_or_absolute,
    is_local_path,
)
from openclaw.agents.utils.sleep import sleep, sleep_sync
from openclaw.agents.utils.syntax_highlight import detect_language


class TestAnsi:
    def test_strip_ansi_no_codes(self):
        assert strip_ansi("hello world") == "hello world"

    def test_strip_ansi_with_codes(self):
        assert strip_ansi("\x1b[31mred\x1b[0m text") == "red text"

    def test_strip_ansi_complex(self):
        assert strip_ansi("\x1b[1;33mHello\x1b[0m \x1b[4mWorld\x1b[0m") == "Hello World"

    def test_strip_ansi_non_string(self):
        with pytest.raises(TypeError):
            strip_ansi(123)  # type: ignore


class TestMime:
    def test_jpeg(self):
        # JPEG SOI marker
        data = bytes([0xFF, 0xD8, 0xFF, 0xE0])
        assert detect_supported_image_mime_type(data) == "image/jpeg"

    def test_png(self):
        # PNG signature + IHDR chunk
        data = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + b"\x00\x00\x00\x0D" + b"IHDR"
        assert detect_supported_image_mime_type(data) == "image/png"

    def test_gif(self):
        data = b"GIF89a"
        assert detect_supported_image_mime_type(data) == "image/gif"

    def test_webp(self):
        data = b"RIFF" + b"\x00" * 4 + b"WEBP"
        assert detect_supported_image_mime_type(data) == "image/webp"

    def test_unknown(self):
        assert detect_supported_image_mime_type(b"not an image") is None

    def test_empty(self):
        assert detect_supported_image_mime_type(b"") is None


class TestPaths:
    def test_canonicalize_path(self):
        result = canonicalize_path("/tmp")
        assert "/tmp" in result or result == "/private/tmp"

    def test_canonicalize_path_invalid(self):
        assert canonicalize_path("/nonexistent/path/that/does/not/exist") == "/nonexistent/path/that/does/not/exist"

    def test_is_local_path(self):
        assert is_local_path("./local/file")
        assert is_local_path("/absolute/path")
        assert not is_local_path("npm:package")
        assert not is_local_path("git://example.com/repo")
        assert not is_local_path("https://example.com")

    def test_format_path_relative_to_cwd(self):
        result = format_path_relative_to_cwd_or_absolute("file.txt", "/tmp")
        assert "file.txt" in result

    def test_format_path_outside_cwd(self):
        result = format_path_relative_to_cwd_or_absolute("/usr/bin/file", "/tmp")
        assert result == "/usr/bin/file"


class TestFrontmatter:
    def test_no_frontmatter(self):
        result = parse_frontmatter("Hello world")
        assert result["frontmatter"] == {}
        assert result["body"] == "Hello world"

    def test_with_frontmatter(self):
        content = "---\ntitle: Test\n---\nBody content"
        result = parse_frontmatter(content)
        assert result["frontmatter"]["title"] == "Test"
        assert result["body"] == "Body content"

    def test_incomplete_frontmatter(self):
        content = "---\ntitle: Test\nBody content"
        result = parse_frontmatter(content)
        assert result["frontmatter"] == {}
        assert "title" in result["body"]

    def test_strip_frontmatter(self):
        content = "---\ntitle: Test\n---\nBody"
        assert strip_frontmatter(content) == "Body"


class TestHtml:
    def test_decode_named_entities(self):
        assert decode_html_entities("&amp;&lt;&gt;&quot;&apos;") == "&<>\"'"

    def test_decode_numeric_entity(self):
        assert decode_html_entities("&#65;") == "A"

    def test_decode_hex_entity(self):
        assert decode_html_entities("&#x41;") == "A"

    def test_decode_entity_at(self):
        result = decode_html_entity_at("&amp;", 0)
        assert result is not None
        assert result["text"] == "&"
        assert result["length"] == 5

    def test_no_entity(self):
        assert decode_html_entities("hello") == "hello"

    def test_mixed(self):
        assert decode_html_entities("a &amp; b &lt; c") == "a & b < c"


class TestGit:
    def test_parse_https_url(self):
        result = parse_git_url("https://github.com/user/repo")
        assert result is not None
        assert result["host"] == "github.com"
        assert result["path"] == "user/repo"

    def test_parse_https_url_with_ref(self):
        result = parse_git_url("https://github.com/user/repo@main")
        assert result is not None
        assert result["ref"] == "main"
        assert result["pinned"] is True

    def test_parse_git_prefix(self):
        result = parse_git_url("git:github.com/user/repo")
        assert result is not None
        assert result["host"] == "github.com"

    def test_parse_scp_like(self):
        result = parse_git_url("git@github.com:user/repo")
        assert result is not None
        assert result["host"] == "github.com"
        assert result["path"] == "user/repo"

    def test_parse_non_git(self):
        assert parse_git_url("npm:package") is None

    def test_parse_plain_string(self):
        assert parse_git_url("just-a-name") is None


class TestSleep:
    async def test_sleep_short(self):
        await sleep(10)

    def test_sleep_sync(self):
        sleep_sync(1)

    async def test_sleep_zero(self):
        await sleep(0)


class TestSyntaxHighlight:
    def test_detect_language_python(self):
        assert detect_language("test.py") == "python"

    def test_detect_language_typescript(self):
        assert detect_language("test.ts") == "typescript"

    def test_detect_language_unknown(self):
        assert detect_language("test.unknown") is None

    def test_detect_language_no_extension(self):
        assert detect_language("Makefile") is None

    def test_highlight_passthrough(self):
        from openclaw.agents.utils.syntax_highlight import highlight

        assert highlight("code", "python") == "code"
