"""DashScope-compatible video provider adapts DashScope-style generation APIs.

Mirrors src/video-generation/dashscope-compatible.ts.
"""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable
from typing import Any

from openclaw.media.configured_max_bytes import resolve_generated_media_max_bytes
from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty
from openclaw.plugin_sdk.provider_http import (
    assert_ok_or_throw_http_error,
    create_provider_operation_deadline,
    create_provider_operation_timeout_resolver,
    fetch_provider_download_response,
    fetch_provider_operation_response,
    post_json_request,
    read_response_with_limit,
    resolve_provider_operation_timeout_ms,
    wait_provider_operation_poll_interval,
)
from openclaw.plugins.contracts.shared import unique_strings

DEFAULT_DASHSCOPE_WAN_VIDEO_MODEL = "wan2.6-t2v"
DASHSCOPE_WAN_VIDEO_MODELS = [
    DEFAULT_DASHSCOPE_WAN_VIDEO_MODEL,
    "wan2.6-i2v",
    "wan2.6-r2v",
    "wan2.6-r2v-flash",
    "wan2.7-r2v",
]
DASHSCOPE_WAN_VIDEO_CAPABILITIES = {
    "generate": {
        "maxVideos": 1,
        "maxDurationSeconds": 10,
        "supportsSize": True,
        "supportsAspectRatio": True,
        "supportsResolution": True,
        "supportsAudio": True,
        "supportsWatermark": True,
    },
    "imageToVideo": {
        "enabled": True,
        "maxVideos": 1,
        "maxInputImages": 1,
        "maxDurationSeconds": 10,
        "supportsSize": True,
        "supportsAspectRatio": True,
        "supportsResolution": True,
        "supportsAudio": True,
        "supportsWatermark": True,
    },
    "videoToVideo": {
        "enabled": True,
        "maxVideos": 1,
        "maxInputVideos": 4,
        "maxDurationSeconds": 10,
        "supportsSize": True,
        "supportsAspectRatio": True,
        "supportsResolution": True,
        "supportsAudio": True,
        "supportsWatermark": True,
    },
}

DEFAULT_VIDEO_GENERATION_DURATION_SECONDS = 5
DEFAULT_VIDEO_GENERATION_TIMEOUT_MS = 120_000
DEFAULT_VIDEO_RESOLUTION_TO_SIZE = {
    "480P": "832*480",
    "720P": "1280*720",
    "1080P": "1920*1080",
}

_DEFAULT_VIDEO_GENERATION_POLL_INTERVAL_MS = 2_500
_DEFAULT_VIDEO_GENERATION_MAX_POLL_ATTEMPTS = 120


def build_dashscope_video_generation_input(params: dict[str, Any]) -> dict[str, Any]:
    """Build DashScope video generation input payload from a normalized request."""
    req = params["req"]
    provider_label = params["providerLabel"]
    input_images = req.get("inputImages") or []
    input_videos = req.get("inputVideos") or []
    unsupported = any(
        not (asset.get("url") or "").strip() and asset.get("buffer") is not None
        for asset in [*input_images, *input_videos]
    )
    if unsupported:
        raise ValueError(
            f"{provider_label} video generation currently requires remote http(s) URLs "
            "for reference images/videos."
        )
    payload: dict[str, Any] = {"prompt": req["prompt"]}
    reference_urls = resolve_video_generation_reference_urls(input_images, input_videos)
    if len(reference_urls) == 1 and len(input_images) == 1 and not input_videos:
        payload["img_url"] = reference_urls[0]
    elif reference_urls:
        payload["reference_urls"] = reference_urls
    return payload


def resolve_video_generation_reference_urls(
    input_images: list[dict[str, Any]] | None,
    input_videos: list[dict[str, Any]] | None,
) -> list[str]:
    """Collect trimmed remote reference URLs from image/video source assets."""
    urls: list[str] = []
    for asset in [*(input_images or []), *(input_videos or [])]:
        url = asset.get("url")
        if isinstance(url, str) and url.strip():
            urls.append(url.strip())
    return urls


def build_dashscope_video_generation_parameters(
    req: dict[str, Any],
    resolution_to_size: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Build DashScope video generation parameter payload from a normalized request."""
    sizes = resolution_to_size or DEFAULT_VIDEO_RESOLUTION_TO_SIZE
    parameters: dict[str, Any] = {}
    size = req.get("size")
    if isinstance(size, str) and size.strip():
        parameters["size"] = size.strip()
    elif req.get("resolution") in sizes:
        parameters["size"] = sizes[str(req["resolution"])]
    aspect_ratio = req.get("aspectRatio")
    if isinstance(aspect_ratio, str) and aspect_ratio.strip():
        parameters["aspect_ratio"] = aspect_ratio.strip()
    duration_seconds = req.get("durationSeconds")
    if isinstance(duration_seconds, (int, float)) and math.isfinite(duration_seconds):
        parameters["duration"] = max(1, round(duration_seconds))
    if isinstance(req.get("audio"), bool):
        parameters["enable_audio"] = req["audio"]
    if isinstance(req.get("watermark"), bool):
        parameters["watermark"] = req["watermark"]
    return parameters or None


def extract_dashscope_video_urls(payload: dict[str, Any]) -> list[str]:
    """Extract unique video URLs from a DashScope task completion payload."""
    output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
    results = output.get("results") if isinstance(output.get("results"), list) else []
    urls: list[str] = []
    for entry in results:
        if isinstance(entry, dict):
            video_url = entry.get("video_url")
            if isinstance(video_url, str) and video_url.strip():
                urls.append(video_url.strip())
    top_level_url = output.get("video_url")
    if isinstance(top_level_url, str) and top_level_url.strip():
        urls.append(top_level_url.strip())
    return unique_strings(urls)


async def poll_dashscope_video_task_until_complete(params: dict[str, Any]) -> dict[str, Any]:
    """Poll a DashScope async video task until it succeeds or fails."""
    provider_label = params["providerLabel"]
    task_id = params["taskId"]
    headers = params["headers"]
    fetch_fn = params["fetchFn"]
    base_url = params["baseUrl"]
    default_timeout_ms = params.get("defaultTimeoutMs", DEFAULT_VIDEO_GENERATION_TIMEOUT_MS)
    deadline = create_provider_operation_deadline(
        timeout_ms=params.get("timeoutMs"),
        label=f"{provider_label} video generation task {task_id}",
    )
    for _attempt in range(_DEFAULT_VIDEO_GENERATION_MAX_POLL_ATTEMPTS):
        response = await fetch_provider_operation_response(
            {
                "stage": "poll",
                "url": f"{base_url}/api/v1/tasks/{task_id}",
                "init": {"method": "GET", "headers": headers},
                "timeoutMs": create_provider_operation_timeout_resolver(
                    deadline=deadline,
                    default_timeout_ms=default_timeout_ms,
                ),
                "fetchFn": fetch_fn,
                "provider": provider_label,
                "requestFailedMessage": f"{provider_label} video-generation task poll failed",
            }
        )
        payload = await response.json()
        if not isinstance(payload, dict):
            raise TypeError(f"{provider_label} video-generation task poll returned invalid JSON")
        output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
        status = normalize_lowercase_string_or_empty(output.get("task_status")).upper()
        if status == "SUCCEEDED":
            return payload
        if status in {"FAILED", "CANCELED"}:
            message = output.get("message") or payload.get("message")
            if isinstance(message, str) and message.strip():
                raise ValueError(message.strip())
            raise ValueError(
                f"{provider_label} video generation task {task_id} "
                f"{normalize_lowercase_string_or_empty(status)}"
            )
        await wait_provider_operation_poll_interval(
            deadline=deadline,
            poll_interval_ms=_DEFAULT_VIDEO_GENERATION_POLL_INTERVAL_MS,
        )
    raise ValueError(f"{provider_label} video generation task {task_id} did not finish in time")


async def download_dashscope_generated_videos(params: dict[str, Any]) -> list[dict[str, Any]]:
    """Download DashScope task result URLs into generated video assets."""
    provider_label = params["providerLabel"]
    urls = params["urls"]
    fetch_fn = params["fetchFn"]
    default_timeout_ms = params.get("defaultTimeoutMs", DEFAULT_VIDEO_GENERATION_TIMEOUT_MS)
    timeout_ms = params.get("timeoutMs", default_timeout_ms)
    max_bytes = params["maxBytes"]
    videos: list[dict[str, Any]] = []
    for index, url in enumerate(urls):
        response = await fetch_provider_download_response(
            {
                "url": url,
                "init": {"method": "GET"},
                "timeoutMs": timeout_ms,
                "fetchFn": fetch_fn,
                "provider": provider_label,
                "requestFailedMessage": f"{provider_label} generated video download failed",
            }
        )
        buffer = await read_response_with_limit(
            response,
            max_bytes,
            on_overflow=lambda info: ValueError(
                f"{provider_label} generated video download exceeds {info['maxBytes']} bytes"
            ),
        )
        content_type = getattr(response, "headers", {}).get("content-type")
        if hasattr(response, "headers") and hasattr(response.headers, "get"):
            content_type = response.headers.get("content-type")
        mime_type = (
            content_type.strip()
            if isinstance(content_type, str) and content_type.strip()
            else "video/mp4"
        )
        videos.append(
            {
                "buffer": buffer,
                "mimeType": mime_type,
                "fileName": f"video-{index + 1}.mp4",
                "metadata": {"sourceUrl": url},
            }
        )
    return videos


async def run_dashscope_video_generation_task(params: dict[str, Any]) -> dict[str, Any]:
    """Submit, poll, and download a DashScope-compatible async video generation task."""
    provider_label = params["providerLabel"]
    model = params["model"]
    req = params["req"]
    fetch_fn = params["fetchFn"]
    headers = params["headers"]
    base_url = params["baseUrl"]
    default_timeout_ms = params.get("defaultTimeoutMs", DEFAULT_VIDEO_GENERATION_TIMEOUT_MS)
    deadline = create_provider_operation_deadline(
        timeout_ms=params.get("timeoutMs"),
        label=f"{provider_label} video generation",
    )
    request = {
        **req,
        "durationSeconds": req.get("durationSeconds", DEFAULT_VIDEO_GENERATION_DURATION_SECONDS),
    }
    result = await post_json_request(
        {
            "url": params["url"],
            "headers": headers,
            "body": {
                "model": model,
                "input": build_dashscope_video_generation_input(
                    {"providerLabel": provider_label, "req": req}
                ),
                "parameters": build_dashscope_video_generation_parameters(
                    request,
                    DEFAULT_VIDEO_RESOLUTION_TO_SIZE,
                ),
            },
            "timeoutMs": resolve_provider_operation_timeout_ms(
                deadline=deadline,
                default_timeout_ms=default_timeout_ms,
            ),
            "fetchFn": fetch_fn,
            "allowPrivateNetwork": params.get("allowPrivateNetwork"),
            "dispatcherPolicy": params.get("dispatcherPolicy"),
        }
    )
    response = result["response"]
    release: Callable[[], Awaitable[None]] = result["release"]
    try:
        await assert_ok_or_throw_http_error(
            response,
            f"{provider_label} video generation failed",
        )
        submitted = await response.json()
        if not isinstance(submitted, dict):
            raise TypeError(f"{provider_label} video generation response missing task_id")
        output = submitted.get("output") if isinstance(submitted.get("output"), dict) else {}
        task_id = output.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError(f"{provider_label} video generation response missing task_id")
        task_id = task_id.strip()
        completed = await poll_dashscope_video_task_until_complete(
            {
                "providerLabel": provider_label,
                "taskId": task_id,
                "headers": headers,
                "timeoutMs": resolve_provider_operation_timeout_ms(
                    deadline=deadline,
                    default_timeout_ms=default_timeout_ms,
                ),
                "fetchFn": fetch_fn,
                "baseUrl": base_url,
                "defaultTimeoutMs": default_timeout_ms,
            }
        )
        urls = extract_dashscope_video_urls(completed)
        if not urls:
            raise ValueError(
                f"{provider_label} video generation completed without output video URLs"
            )
        videos = await download_dashscope_generated_videos(
            {
                "providerLabel": provider_label,
                "urls": urls,
                "timeoutMs": create_provider_operation_timeout_resolver(
                    deadline=deadline,
                    default_timeout_ms=default_timeout_ms,
                ),
                "fetchFn": fetch_fn,
                "defaultTimeoutMs": default_timeout_ms,
                "maxBytes": resolve_generated_media_max_bytes(req.get("cfg"), "video"),
            }
        )
        completed_output = (
            completed.get("output") if isinstance(completed.get("output"), dict) else {}
        )
        return {
            "videos": videos,
            "model": model,
            "metadata": {
                "requestId": submitted.get("request_id"),
                "taskId": task_id,
                "taskStatus": completed_output.get("task_status"),
            },
        }
    finally:
        await release()
