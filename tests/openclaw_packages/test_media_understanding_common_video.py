"""Tests for media-understanding video payload sizing."""

from __future__ import annotations

from openclaw_packages.media_understanding_common import (
    DEFAULT_VIDEO_MAX_BASE64_BYTES,
    estimate_base64_size,
    resolve_video_max_base64_bytes,
)


def test_rounds_byte_counts_to_base64_quanta() -> None:
    assert estimate_base64_size(1) == 4
    assert estimate_base64_size(2) == 4
    assert estimate_base64_size(3) == 4
    assert estimate_base64_size(4) == 8


def test_allows_raw_byte_limits_that_expand_to_valid_base64_boundaries() -> None:
    assert resolve_video_max_base64_bytes(1) == 4
    assert resolve_video_max_base64_bytes(2) == 4
    assert resolve_video_max_base64_bytes(3) == 4
    assert resolve_video_max_base64_bytes(4) == 8


def test_keeps_shared_maximum_base64_payload_cap() -> None:
    assert (
        resolve_video_max_base64_bytes(DEFAULT_VIDEO_MAX_BASE64_BYTES)
        == DEFAULT_VIDEO_MAX_BASE64_BYTES
    )
