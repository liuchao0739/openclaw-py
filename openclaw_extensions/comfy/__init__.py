"""ComfyUI provider extension."""

from openclaw_extensions.comfy.image_generation_provider import (
    build_comfy_image_generation_provider,
)
from openclaw_extensions.comfy.music_generation_provider import (
    build_comfy_music_generation_provider,
)
from openclaw_extensions.comfy.test_helpers import (
    build_comfy_config,
    build_legacy_comfy_config,
    mock_comfy_cloud_job_responses,
    mock_comfy_provider_api_key,
    parse_comfy_json_body,
)
from openclaw_extensions.comfy.video_generation_provider import (
    build_comfy_video_generation_provider,
)
from openclaw_extensions.comfy.workflow_runtime import (
    DEFAULT_COMFY_MODEL,
    get_comfy_config,
    is_comfy_capability_configured,
    run_comfy_workflow,
    set_comfy_fetch_guard_for_testing,
)

__all__ = [
    "DEFAULT_COMFY_MODEL",
    "build_comfy_config",
    "build_comfy_image_generation_provider",
    "build_comfy_music_generation_provider",
    "build_comfy_video_generation_provider",
    "build_legacy_comfy_config",
    "get_comfy_config",
    "is_comfy_capability_configured",
    "mock_comfy_cloud_job_responses",
    "mock_comfy_provider_api_key",
    "parse_comfy_json_body",
    "run_comfy_workflow",
    "set_comfy_fetch_guard_for_testing",
]
