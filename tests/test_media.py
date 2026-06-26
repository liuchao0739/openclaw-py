"""Tests for media modules."""

import asyncio
import base64
import os

import pytest

from openclaw.media.ffmpeg_limits import (
    MEDIA_FFMPEG_MAX_BUFFER_BYTES,
    MEDIA_FFPROBE_TIMEOUT_MS,
    MEDIA_FFMPEG_TIMEOUT_MS,
    MEDIA_FFMPEG_MAX_AUDIO_DURATION_SECS,
)
from openclaw.media.temp_files import unlink_if_exists
from openclaw.media.sniff_mime_from_base64 import sniff_mime_from_base64


class TestFfmpegLimits:
    def test_constants(self):
        assert MEDIA_FFMPEG_MAX_BUFFER_BYTES == 10 * 1024 * 1024
        assert MEDIA_FFPROBE_TIMEOUT_MS == 10_000
        assert MEDIA_FFMPEG_TIMEOUT_MS == 45_000
        assert MEDIA_FFMPEG_MAX_AUDIO_DURATION_SECS == 1200


class TestUnlinkIfExists:
    def test_none(self):
        asyncio.run(unlink_if_exists(None))  # should not raise

    def test_empty(self):
        asyncio.run(unlink_if_exists(""))  # should not raise

    def test_existing_file(self, tmp_path):
        f = tmp_path / "temp.txt"
        f.write_text("x")
        asyncio.run(unlink_if_exists(str(f)))
        assert not f.exists()

    def test_nonexistent_file(self):
        asyncio.run(unlink_if_exists("/nonexistent/file"))  # should not raise


class TestSniffMimeFromBase64:
    def test_png(self):
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        b64 = base64.b64encode(png_header).decode()
        result = asyncio.run(sniff_mime_from_base64(b64))
        assert result == "image/png"

    def test_jpeg(self):
        jpeg_header = b"\xff\xd8\xff\xe0" + b"\x00" * 20
        b64 = base64.b64encode(jpeg_header).decode()
        result = asyncio.run(sniff_mime_from_base64(b64))
        assert result == "image/jpeg"

    def test_gif(self):
        gif_header = b"GIF89a" + b"\x00" * 20
        b64 = base64.b64encode(gif_header).decode()
        result = asyncio.run(sniff_mime_from_base64(b64))
        assert result == "image/gif"

    def test_pdf(self):
        pdf_header = b"%PDF-1.4" + b"\x00" * 20
        b64 = base64.b64encode(pdf_header).decode()
        result = asyncio.run(sniff_mime_from_base64(b64))
        assert result == "application/pdf"

    def test_empty(self):
        assert asyncio.run(sniff_mime_from_base64("")) is None
        assert asyncio.run(sniff_mime_from_base64("   ")) is None

    def test_non_string(self):
        assert asyncio.run(sniff_mime_from_base64(123)) is None

    def test_too_short(self):
        assert asyncio.run(sniff_mime_from_base64("AAAA")) is None

    def test_unknown_format(self):
        data = b"\x00\x01\x02\x03" + b"\x00" * 20
        b64 = base64.b64encode(data).decode()
        assert asyncio.run(sniff_mime_from_base64(b64)) is None

    def test_with_whitespace(self):
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        b64 = base64.b64encode(png_header).decode()
        # Add whitespace
        b64_ws = b64[:10] + "\n" + b64[10:]
        result = asyncio.run(sniff_mime_from_base64(b64_ws))
        assert result == "image/png"
