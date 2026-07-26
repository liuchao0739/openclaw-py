"""Provider test contracts re-export shared assertion helpers."""

from openclaw.plugin_sdk.test_helpers.dashscope_video_provider import (
    expect_dashscope_video_task_poll,
    expect_successful_dashscope_video_result,
    mock_successful_dashscope_video_task,
)
from openclaw.plugin_sdk.test_helpers.provider_media_capability_assertions import (
    expect_explicit_video_generation_capabilities,
)

__all__ = [
    "expect_dashscope_video_task_poll",
    "expect_explicit_video_generation_capabilities",
    "expect_successful_dashscope_video_result",
    "mock_successful_dashscope_video_task",
]
