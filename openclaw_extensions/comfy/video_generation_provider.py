"""Comfy video generation provider."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.comfy.workflow_runtime import (
    DEFAULT_COMFY_MODEL,
    is_comfy_capability_configured,
    run_comfy_workflow,
    set_comfy_fetch_guard_for_testing,
)

__all__ = [
    "build_comfy_video_generation_provider",
    "set_comfy_fetch_guard_for_testing",
]


def _to_comfy_input_image(input_image: dict[str, Any] | None) -> dict[str, Any] | None:
    if not input_image:
        return None
    if not input_image.get("buffer") or not input_image.get("mimeType"):
        raise RuntimeError("Comfy video generation requires a local reference image file")
    return {
        "buffer": input_image["buffer"],
        "mimeType": input_image["mimeType"],
        "fileName": input_image.get("fileName"),
    }


def build_comfy_video_generation_provider() -> dict[str, Any]:
    async def generate_video(req: dict[str, Any]) -> dict[str, Any]:
        input_images = req.get("inputImages")
        input_videos = req.get("inputVideos")
        if isinstance(input_images, list) and len(input_images) > 1:
            raise RuntimeError(
                "Comfy video generation currently supports at most one reference image",
            )
        if isinstance(input_videos, list) and len(input_videos) > 0:
            raise RuntimeError("Comfy video generation does not support input videos")
        first_image = input_images[0] if isinstance(input_images, list) and input_images else None
        result = await run_comfy_workflow(
            {
                "cfg": req["cfg"],
                "agentDir": req.get("agentDir"),
                "authStore": req.get("authStore"),
                "prompt": req["prompt"],
                "model": req.get("model"),
                "timeoutMs": req.get("timeoutMs"),
                "capability": "video",
                "outputKinds": ["gifs", "videos"],
                "inputImage": _to_comfy_input_image(first_image),
            }
        )
        videos = [
            {
                "buffer": asset["buffer"],
                "mimeType": asset["mimeType"],
                "fileName": asset["fileName"],
                "metadata": {
                    "nodeId": asset["nodeId"],
                    "promptId": result["promptId"],
                },
            }
            for asset in result["assets"]
        ]
        return {
            "videos": videos,
            "model": result["model"],
            "metadata": {
                "promptId": result["promptId"],
                "outputNodeIds": result["outputNodeIds"],
            },
        }

    return {
        "id": "comfy",
        "label": "ComfyUI",
        "defaultModel": DEFAULT_COMFY_MODEL,
        "models": [DEFAULT_COMFY_MODEL],
        "isConfigured": lambda ctx: is_comfy_capability_configured(
            {
                "cfg": ctx.get("cfg"),
                "agentDir": ctx.get("agentDir"),
                "capability": "video",
            }
        ),
        "capabilities": {
            "generate": {
                "maxVideos": 1,
                "supportsSize": False,
                "supportsAspectRatio": False,
                "supportsResolution": False,
                "supportsAudio": False,
                "supportsWatermark": False,
            },
            "imageToVideo": {
                "enabled": True,
                "maxVideos": 1,
                "maxInputImages": 1,
                "supportsSize": False,
                "supportsAspectRatio": False,
                "supportsResolution": False,
                "supportsAudio": False,
                "supportsWatermark": False,
            },
            "videoToVideo": {
                "enabled": False,
            },
        },
        "generateVideo": generate_video,
    }
