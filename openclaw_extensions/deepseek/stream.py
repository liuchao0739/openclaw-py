"""DeepSeek plugin stream behavior."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from openclaw.plugin_sdk.provider_stream_shared import (
    create_deep_seek_v4_openai_compatible_thinking_wrapper,
)
from openclaw_extensions.deepseek.models import is_deep_seek_v4_model_ref


def create_deep_seek_v4_thinking_wrapper(
    base_stream_fn: Callable[..., Any] | None,
    thinking_level: Any,
) -> Callable[..., Any] | None:
    return create_deep_seek_v4_openai_compatible_thinking_wrapper(
        base_stream_fn=base_stream_fn,
        thinking_level=thinking_level,
        should_patch_model=is_deep_seek_v4_model_ref,
    )
