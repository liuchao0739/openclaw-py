"""Video generation capability helpers derive supported modes.

Mirrors src/video-generation/capabilities.ts (mode listing subset).
"""

from __future__ import annotations

from typing import Any, Literal

VideoGenerationMode = Literal["generate", "imageToVideo", "videoToVideo"]


def list_supported_video_generation_modes(
    provider: dict[str, Any],
) -> list[VideoGenerationMode]:
    """List generation modes enabled by a provider's capability flags."""
    capabilities = provider.get("capabilities") or {}
    modes: list[VideoGenerationMode] = ["generate"]
    image_to_video = capabilities.get("imageToVideo")
    if isinstance(image_to_video, dict) and image_to_video.get("enabled"):
        modes.append("imageToVideo")
    video_to_video = capabilities.get("videoToVideo")
    if isinstance(video_to_video, dict) and video_to_video.get("enabled"):
        modes.append("videoToVideo")
    return modes
