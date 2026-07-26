"""Public video-generation helpers and types for provider plugins.

Mirrors src/plugin-sdk/video-generation.ts exports used by bundled providers.
"""

from openclaw.video_generation.dashscope_compatible import (
    DASHSCOPE_WAN_VIDEO_CAPABILITIES,
    DASHSCOPE_WAN_VIDEO_MODELS,
    DEFAULT_DASHSCOPE_WAN_VIDEO_MODEL,
    DEFAULT_VIDEO_GENERATION_DURATION_SECONDS,
    DEFAULT_VIDEO_GENERATION_TIMEOUT_MS,
    DEFAULT_VIDEO_RESOLUTION_TO_SIZE,
    build_dashscope_video_generation_input,
    build_dashscope_video_generation_parameters,
    download_dashscope_generated_videos,
    extract_dashscope_video_urls,
    poll_dashscope_video_task_until_complete,
    resolve_video_generation_reference_urls,
    run_dashscope_video_generation_task,
)

__all__ = [
    "DASHSCOPE_WAN_VIDEO_CAPABILITIES",
    "DASHSCOPE_WAN_VIDEO_MODELS",
    "DEFAULT_DASHSCOPE_WAN_VIDEO_MODEL",
    "DEFAULT_VIDEO_GENERATION_DURATION_SECONDS",
    "DEFAULT_VIDEO_GENERATION_TIMEOUT_MS",
    "DEFAULT_VIDEO_RESOLUTION_TO_SIZE",
    "build_dashscope_video_generation_input",
    "build_dashscope_video_generation_parameters",
    "download_dashscope_generated_videos",
    "extract_dashscope_video_urls",
    "poll_dashscope_video_task_until_complete",
    "resolve_video_generation_reference_urls",
    "run_dashscope_video_generation_task",
]
