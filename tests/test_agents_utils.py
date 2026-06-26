"""Tests for agents/utils and tools_root."""

import asyncio

import pytest

from openclaw.agents.utils.sleep import sleep
from openclaw.agents.utils.frontmatter import parse_frontmatter, strip_frontmatter


class TestSleep:
    @pytest.mark.asyncio
    async def test_basic_sleep(self):
        await sleep(10)

    @pytest.mark.asyncio
    async def test_zero_sleep(self):
        await sleep(0)

    @pytest.mark.asyncio
    async def test_negative_sleep(self):
        await sleep(-10)

    @pytest.mark.asyncio
    async def test_abort(self):
        event = asyncio.Event()
        event.set()
        try:
            await sleep(1000, event)
            assert False
        except (asyncio.CancelledError, Exception):
            pass


class TestParseFrontmatter:
    def test_no_frontmatter(self):
        result = parse_frontmatter("hello world")
        assert result["frontmatter"] == {}
        assert result["body"] == "hello world"

    def test_with_frontmatter(self):
        content = "---\nkey: value\n---\nbody text"
        result = parse_frontmatter(content)
        assert result["frontmatter"]["key"] == "value"
        assert result["body"] == "body text"

    def test_incomplete_frontmatter(self):
        content = "---\nkey: value\nno closing"
        result = parse_frontmatter(content)
        assert result["frontmatter"] == {}

    def test_strip(self):
        content = "---\nkey: value\n---\nbody"
        assert strip_frontmatter(content) == "body"

    def test_strip_no_frontmatter(self):
        assert strip_frontmatter("hello") == "hello"

    def test_crlf_normalization(self):
        content = "---\r\nkey: value\r\n---\r\nbody"
        result = parse_frontmatter(content)
        assert result["frontmatter"]["key"] == "value"
        assert result["body"] == "body"

    def test_empty_frontmatter(self):
        content = "---\n---\nbody"
        result = parse_frontmatter(content)
        assert result["body"] == "body"

    def test_complex_frontmatter(self):
        content = "---\nname: test\nversion: 1\ntags:\n  - a\n  - b\n---\ncontent"
        result = parse_frontmatter(content)
        assert result["frontmatter"]["name"] == "test"
        assert result["frontmatter"]["tags"] == ["a", "b"]
