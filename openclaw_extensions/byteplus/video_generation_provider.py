"""BytePlus Seedance video generation provider implementation."""

from __future__ import annotations

import base64
import json
import math
import mimetypes
from typing import Any, Literal

from openclaw.packages.normalization_core import is_record, normalize_optional_string
from openclaw.plugin_sdk.provider_auth import is_provider_api_key_configured
from openclaw.plugin_sdk.provider_auth_runtime import resolve_api_key_for_provider
from openclaw.plugin_sdk.provider_http import (
    ProviderOperationDeadline,
    assert_ok_or_throw_http_error,
    create_provider_operation_deadline,
    create_provider_operation_timeout_resolver,
    default_fetch_fn,
    fetch_provider_download_response,
    fetch_provider_operation_response,
    post_json_request,
    read_response_with_limit,
    resolve_provider_http_request_config,
    resolve_provider_operation_timeout_ms,
    wait_provider_operation_poll_interval,
)
from openclaw_extensions.byteplus.models import BYTEPLUS_BASE_URL

DEFAULT_BYTEPLUS_VIDEO_MODEL = "seedance-1-0-lite-t2v-250428"
DEFAULT_TIMEOUT_MS = 120_000
POLL_INTERVAL_MS = 5_000
MAX_POLL_ATTEMPTS = 120
BYTEPLUS_SEED_MAX = 2_147_483_647
BYTEPLUS_MIN_DURATION_SECONDS = 2
BYTEPLUS_MAX_DURATION_SECONDS = 12
DEFAULT_GENERATED_VIDEO_MAX_BYTES = 16 * 1024 * 1024
PROVIDER_JSON_RESPONSE_MAX_BYTES = 16 * 1024 * 1024

BytePlusTaskStatus = Literal["running", "failed", "queued", "succeeded", "cancelled"]


def _as_safe_integer_in_range(
    value: Any,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < -(2**53) or value > 2**53:
        return None
    if min_value is not None and value < min_value:
        return None
    if max_value is not None and value > max_value:
        return None
    return value


async def _read_byteplus_json_response(response: Any, label: str) -> dict[str, Any]:
    def on_overflow(params: dict[str, int]) -> Exception:
        return RuntimeError(f"{label}: JSON response exceeds {params['maxBytes']} bytes")

    raw = await read_response_with_limit(
        response,
        PROVIDER_JSON_RESPONSE_MAX_BYTES,
        on_overflow=on_overflow,
    )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as cause:
        raise RuntimeError(f"{label}: malformed JSON response") from cause
    if not is_record(payload):
        raise RuntimeError(f"{label}: malformed JSON response")
    return payload


def _read_byteplus_task_status(payload: dict[str, Any]) -> BytePlusTaskStatus:
    status = normalize_optional_string(payload.get("status"))
    if status in ("running", "failed", "queued", "succeeded", "cancelled"):
        return status
    if status is None:
        raise ValueError("BytePlus video status response missing task status")
    raise ValueError(f"BytePlus video status response returned unknown task status: {status}")


def _read_byteplus_error_message(error: Any) -> str | None:
    return normalize_optional_string(error.get("message")) if is_record(error) else None


def _read_byteplus_video_url(payload: dict[str, Any]) -> str:
    content = payload.get("content")
    if content is not None and not is_record(content):
        raise ValueError("BytePlus video generation completed with malformed content")
    video_url = normalize_optional_string(content.get("video_url") if is_record(content) else None)
    if not video_url:
        raise ValueError("BytePlus video generation completed without a video URL")
    return video_url


def _resolve_byteplus_video_base_url(req: dict[str, Any]) -> str:
    cfg = req.get("cfg") if is_record(req.get("cfg")) else {}
    models = cfg.get("models") if is_record(cfg.get("models")) else {}
    providers = models.get("providers") if is_record(models.get("providers")) else {}
    byteplus = providers.get("byteplus") if is_record(providers.get("byteplus")) else {}
    return normalize_optional_string(byteplus.get("baseUrl")) or BYTEPLUS_BASE_URL


def _resolve_generated_video_max_bytes(req: dict[str, Any]) -> int:
    cfg = req.get("cfg") if is_record(req.get("cfg")) else {}
    agents = cfg.get("agents") if is_record(cfg.get("agents")) else {}
    defaults = agents.get("defaults") if is_record(agents.get("defaults")) else {}
    configured = defaults.get("mediaMaxMb")
    if isinstance(configured, (int, float)) and configured > 0:
        return int(configured * 1024 * 1024)
    return DEFAULT_GENERATED_VIDEO_MAX_BYTES


def _extension_for_mime(mime_type: str | None) -> str | None:
    normalized = normalize_optional_string(mime_type)
    if not normalized:
        return None
    extension = mimetypes.guess_extension(normalized.split(";", 1)[0].strip())
    return extension


def _to_data_url(buffer: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(buffer).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _resolve_byteplus_image_url(req: dict[str, Any]) -> str | None:
    input_images = req.get("inputImages")
    if not isinstance(input_images, list) or not input_images:
        return None
    first = input_images[0]
    if not is_record(first):
        return None
    input_url = normalize_optional_string(first.get("url"))
    if input_url:
        return input_url
    buffer = first.get("buffer")
    if not buffer:
        raise ValueError("BytePlus reference image is missing image data.")
    if isinstance(buffer, str):
        buffer_bytes = buffer.encode("utf-8")
    elif isinstance(buffer, (bytes, bytearray)):
        buffer_bytes = bytes(buffer)
    else:
        raise ValueError("BytePlus reference image is missing image data.")  # noqa: TRY004
    mime_type = normalize_optional_string(first.get("mimeType")) or "image/png"
    return _to_data_url(buffer_bytes, mime_type)


def _resolve_byteplus_seed(value: Any) -> int | None:
    return _as_safe_integer_in_range(value, min_value=-1, max_value=BYTEPLUS_SEED_MAX)


def _resolve_byteplus_duration_seconds(value: Any) -> int | None:
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return _as_safe_integer_in_range(
        round(value),
        min_value=BYTEPLUS_MIN_DURATION_SECONDS,
        max_value=BYTEPLUS_MAX_DURATION_SECONDS,
    )


def _read_byteplus_duration_seconds(value: Any) -> int | None:
    return _as_safe_integer_in_range(
        value,
        min_value=BYTEPLUS_MIN_DURATION_SECONDS,
        max_value=BYTEPLUS_MAX_DURATION_SECONDS,
    )


async def _poll_byteplus_task(
    *,
    task_id: str,
    headers: dict[str, str],
    timeout_ms: int | None,
    base_url: str,
    fetch_fn: Any,
    deadline: ProviderOperationDeadline,
) -> dict[str, Any]:
    for _attempt in range(MAX_POLL_ATTEMPTS):
        response = await fetch_provider_operation_response(
            {
                "stage": "poll",
                "url": f"{base_url}/contents/generations/tasks/{task_id}",
                "init": {
                    "method": "GET",
                    "headers": headers,
                },
                "timeoutMs": create_provider_operation_timeout_resolver(
                    deadline=deadline,
                    default_timeout_ms=DEFAULT_TIMEOUT_MS,
                ),
                "fetchFn": fetch_fn,
                "provider": "byteplus",
                "requestFailedMessage": "BytePlus video status request failed",
            }
        )
        payload = await _read_byteplus_json_response(
            response,
            "BytePlus video status request failed",
        )
        status = _read_byteplus_task_status(payload)
        if status == "succeeded":
            return payload
        if status in ("failed", "cancelled"):
            raise RuntimeError(
                _read_byteplus_error_message(payload.get("error")) or "BytePlus video generation failed"
            )
        await wait_provider_operation_poll_interval(
            deadline=deadline,
            poll_interval_ms=POLL_INTERVAL_MS,
        )
    raise RuntimeError(f"BytePlus video generation task {task_id} did not finish in time")


async def _download_byteplus_video(
    *,
    url: str,
    timeout_ms: int | None,
    fetch_fn: Any,
    max_bytes: int,
) -> dict[str, Any]:
    response = await fetch_provider_download_response(
        {
            "url": url,
            "init": {"method": "GET"},
            "timeoutMs": timeout_ms or DEFAULT_TIMEOUT_MS,
            "fetchFn": fetch_fn,
            "provider": "byteplus",
            "requestFailedMessage": "BytePlus generated video download failed",
        }
    )
    headers = getattr(response, "headers", {}) or {}
    content_type = headers.get("content-type") if isinstance(headers, dict) else None
    mime_type = normalize_optional_string(content_type) or "video/mp4"
    buffer = await read_response_with_limit(
        response,
        max_bytes,
        on_overflow=lambda params: RuntimeError(
            f"BytePlus generated video download exceeds {params['maxBytes']} bytes"
        ),
    )
    extension = _extension_for_mime(mime_type)
    suffix = extension[1:] if extension and extension.startswith(".") else (extension or "mp4")
    return {
        "buffer": buffer,
        "mimeType": mime_type,
        "fileName": f"video-1.{suffix}",
    }


def build_byte_plus_video_generation_provider() -> dict[str, Any]:
    """Build the BytePlus video generation provider registered by the plugin."""

    async def generate_video(req: dict[str, Any]) -> dict[str, Any]:
        input_videos = req.get("inputVideos")
        if isinstance(input_videos, list) and len(input_videos) > 0:
            raise ValueError("BytePlus video generation does not support video reference inputs.")

        auth = await resolve_api_key_for_provider(
            {
                "provider": "byteplus",
                "cfg": req.get("cfg"),
                "agentDir": req.get("agentDir"),
                "store": req.get("authStore"),
            }
        )
        api_key = auth.get("apiKey")
        if not api_key:
            raise ValueError("BytePlus API key missing")

        fetch_fn = default_fetch_fn
        deadline = create_provider_operation_deadline(
            timeout_ms=req.get("timeoutMs"),
            label="BytePlus video generation",
        )
        request_config = resolve_provider_http_request_config(
            {
                "baseUrl": _resolve_byteplus_video_base_url(req),
                "defaultBaseUrl": BYTEPLUS_BASE_URL,
                "allowPrivateNetwork": False,
                "defaultHeaders": {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                "provider": "byteplus",
                "capability": "video",
                "transport": "http",
            }
        )
        base_url = request_config["baseUrl"]
        headers = request_config["headers"]
        allow_private_network = request_config["allowPrivateNetwork"]
        dispatcher_policy = request_config["dispatcherPolicy"]

        input_images = req.get("inputImages")
        has_input_images = isinstance(input_images, list) and len(input_images) > 0
        requested_model = normalize_optional_string(req.get("model")) or DEFAULT_BYTEPLUS_VIDEO_MODEL
        resolved_model = (
            requested_model.replace("-t2v-", "-i2v-")
            if has_input_images and "-t2v-" in requested_model
            else requested_model
        )

        content: list[dict[str, Any]] = [{"type": "text", "text": req.get("prompt", "")}]
        image_url = _resolve_byteplus_image_url(req)
        if image_url:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                    "role": "first_frame",
                }
            )

        body: dict[str, Any] = {
            "model": resolved_model,
            "content": content,
        }
        aspect_ratio = normalize_optional_string(req.get("aspectRatio"))
        if aspect_ratio:
            body["ratio"] = aspect_ratio
        resolution = normalize_optional_string(req.get("resolution"))
        if resolution:
            body["resolution"] = resolution.lower()
        duration = _resolve_byteplus_duration_seconds(req.get("durationSeconds"))
        if duration is not None:
            body["duration"] = duration
        if isinstance(req.get("audio"), bool):
            body["generate_audio"] = req["audio"]
        if isinstance(req.get("watermark"), bool):
            body["watermark"] = req["watermark"]

        provider_options = req.get("providerOptions")
        opts = provider_options if is_record(provider_options) else {}
        seed = _resolve_byteplus_seed(opts.get("seed"))
        draft = opts.get("draft") is True
        camera_fixed = opts.get("camera_fixed")
        camera_fixed_value = camera_fixed if isinstance(camera_fixed, bool) else None
        if seed is not None:
            body["seed"] = seed
        if draft and "resolution" not in body:
            body["resolution"] = "480p"
        if camera_fixed_value is not None:
            body["camera_fixed"] = camera_fixed_value

        submitted_response = await post_json_request(
            {
                "url": f"{base_url}/contents/generations/tasks",
                "headers": headers,
                "body": body,
                "timeoutMs": resolve_provider_operation_timeout_ms(
                    deadline=deadline,
                    default_timeout_ms=DEFAULT_TIMEOUT_MS,
                ),
                "fetchFn": fetch_fn,
                "allowPrivateNetwork": allow_private_network,
                "dispatcherPolicy": dispatcher_policy,
            }
        )
        response = submitted_response["response"]
        release = submitted_response["release"]
        try:
            await assert_ok_or_throw_http_error(response, "BytePlus video generation failed")
            submitted = await _read_byteplus_json_response(
                response,
                "BytePlus video generation failed",
            )
            task_id = normalize_optional_string(submitted.get("id"))
            if not task_id:
                raise ValueError("BytePlus video generation response missing task id")
            completed = await _poll_byteplus_task(
                task_id=task_id,
                headers=headers,
                timeout_ms=resolve_provider_operation_timeout_ms(
                    deadline=deadline,
                    default_timeout_ms=DEFAULT_TIMEOUT_MS,
                ),
                base_url=base_url,
                fetch_fn=fetch_fn,
                deadline=deadline,
            )
            video_url = _read_byteplus_video_url(completed)
            video = await _download_byteplus_video(
                url=video_url,
                timeout_ms=create_provider_operation_timeout_resolver(
                    deadline=deadline,
                    default_timeout_ms=DEFAULT_TIMEOUT_MS,
                )(),
                fetch_fn=fetch_fn,
                max_bytes=_resolve_generated_video_max_bytes(req),
            )
            return {
                "videos": [video],
                "model": normalize_optional_string(completed.get("model")) or resolved_model,
                "metadata": {
                    "taskId": task_id,
                    "status": normalize_optional_string(completed.get("status")),
                    "videoUrl": video_url,
                    "ratio": normalize_optional_string(completed.get("ratio")),
                    "resolution": normalize_optional_string(completed.get("resolution")),
                    "duration": _read_byteplus_duration_seconds(completed.get("duration")),
                },
            }
        finally:
            await release()

    return {
        "id": "byteplus",
        "label": "BytePlus",
        "defaultModel": DEFAULT_BYTEPLUS_VIDEO_MODEL,
        "models": [
            DEFAULT_BYTEPLUS_VIDEO_MODEL,
            "seedance-1-0-lite-i2v-250428",
            "seedance-1-0-pro-250528",
            "seedance-1-5-pro-251215",
        ],
        "isConfigured": lambda ctx: is_provider_api_key_configured(
            {
                "provider": "byteplus",
                "agentDir": ctx.get("agentDir"),
            }
        ),
        "capabilities": {
            "providerOptions": {
                "seed": "number",
                "draft": "boolean",
                "camera_fixed": "boolean",
            },
            "generate": {
                "maxVideos": 1,
                "maxDurationSeconds": 12,
                "supportsAspectRatio": True,
                "supportsResolution": True,
                "supportsAudio": True,
                "supportsWatermark": True,
            },
            "imageToVideo": {
                "enabled": True,
                "maxVideos": 1,
                "maxInputImages": 1,
                "maxDurationSeconds": 12,
                "supportsAspectRatio": True,
                "supportsResolution": True,
                "supportsAudio": True,
                "supportsWatermark": True,
            },
            "videoToVideo": {
                "enabled": False,
            },
        },
        "generateVideo": generate_video,
    }
