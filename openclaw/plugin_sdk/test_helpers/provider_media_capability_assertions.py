"""Assertions for video and music provider media capability contracts.

Mirrors src/plugin-sdk/test-helpers/provider-media-capability-assertions.ts.
"""

from __future__ import annotations

import math
from typing import Any

from openclaw.video_generation.capabilities import list_supported_video_generation_modes


def _has_positive_mode_limit(
    value: int | None,
    values_by_model: dict[str, int] | None,
) -> bool:
    if (value or 0) > 0:
        return True
    return any(
        isinstance(model_value, (int, float))
        and math.isfinite(model_value)
        and model_value > 0
        for model_value in (values_by_model or {}).values()
    )


def expect_explicit_video_generation_capabilities(provider: dict[str, Any]) -> None:
    """Verify a video provider declares coherent generate/image/video capability flags."""
    provider_id = provider.get("id", "provider")
    capabilities = provider.get("capabilities") or {}
    assert capabilities.get("generate") is not None, f"{provider_id} missing generate capabilities"
    assert capabilities.get("imageToVideo") is not None, (
        f"{provider_id} missing imageToVideo capabilities"
    )
    assert capabilities.get("videoToVideo") is not None, (
        f"{provider_id} missing videoToVideo capabilities"
    )

    supported_modes = list_supported_video_generation_modes(provider)
    image_to_video = capabilities.get("imageToVideo")
    video_to_video = capabilities.get("videoToVideo")
    if isinstance(image_to_video, dict) and image_to_video.get("enabled"):
        assert _has_positive_mode_limit(
            image_to_video.get("maxInputImages"),
            image_to_video.get("maxInputImagesByModel"),
        ), f"{provider_id} imageToVideo.enabled requires maxInputImages or maxInputImagesByModel"
        assert "imageToVideo" in supported_modes
    if isinstance(video_to_video, dict) and video_to_video.get("enabled"):
        assert _has_positive_mode_limit(
            video_to_video.get("maxInputVideos"),
            video_to_video.get("maxInputVideosByModel"),
        ), f"{provider_id} videoToVideo.enabled requires maxInputVideos or maxInputVideosByModel"
        assert "videoToVideo" in supported_modes
