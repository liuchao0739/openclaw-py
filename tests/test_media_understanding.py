"""Tests for media-understanding modules."""

import asyncio
import os

import pytest

from openclaw.media_understanding.fs import file_exists
from openclaw.media_understanding.provider_id import normalize_media_provider_id


class TestFileExists:
    def test_none(self):
        assert asyncio.run(file_exists(None)) is False

    def test_empty(self):
        assert asyncio.run(file_exists("")) is False

    def test_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("x")
        assert asyncio.run(file_exists(str(f))) is True

    def test_nonexistent_file(self):
        assert asyncio.run(file_exists("/nonexistent/file")) is False


class TestNormalizeMediaProviderId:
    def test_valid(self):
        assert normalize_media_provider_id("openai") == "openai"

    def test_uppercase(self):
        assert normalize_media_provider_id("OpenAI") == "openai"

    def test_with_spaces(self):
        assert normalize_media_provider_id("  google  ") == "google"

    def test_empty(self):
        assert normalize_media_provider_id("") is None
        assert normalize_media_provider_id("   ") is None

    def test_non_string(self):
        assert normalize_media_provider_id(123) is None
        assert normalize_media_provider_id(None) is None
