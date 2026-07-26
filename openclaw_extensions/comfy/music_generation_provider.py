"""Comfy music generation provider."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.comfy.workflow_runtime import (
    DEFAULT_COMFY_MODEL,
    is_comfy_capability_configured,
    run_comfy_workflow,
)

COMFY_MAX_INPUT_IMAGES = 1


def _to_generated_track(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "buffer": asset["buffer"],
        "mimeType": asset["mimeType"],
        "fileName": asset["fileName"],
    }


def _resolve_input_image(input_image: dict[str, Any] | None) -> dict[str, Any] | None:
    if not input_image:
        return None
    if not input_image.get("buffer"):
        raise RuntimeError("Comfy music generation requires loaded reference image bytes.")
    return {
        "buffer": input_image["buffer"],
        "mimeType": input_image.get("mimeType") or "image/png",
        "fileName": input_image.get("fileName"),
    }


def build_comfy_music_generation_provider() -> dict[str, Any]:
    async def generate_music(req: dict[str, Any]) -> dict[str, Any]:
        input_images = req.get("inputImages")
        if isinstance(input_images, list) and len(input_images) > COMFY_MAX_INPUT_IMAGES:
            raise RuntimeError(
                f"Comfy music generation supports at most {COMFY_MAX_INPUT_IMAGES} reference image.",
            )
        first_image = input_images[0] if isinstance(input_images, list) and input_images else None
        result = await run_comfy_workflow(
            {
                "cfg": req["cfg"],
                "agentDir": req.get("agentDir"),
                "authStore": req.get("authStore"),
                "prompt": req["prompt"],
                "model": req.get("model"),
                "capability": "music",
                "outputKinds": ["audio"],
                "inputImage": _resolve_input_image(first_image),
            }
        )
        return {
            "tracks": [_to_generated_track(asset) for asset in result["assets"]],
            "model": result["model"],
            "metadata": {
                "promptId": result["promptId"],
                "outputNodeIds": result["outputNodeIds"],
                "inputImageCount": len(input_images) if isinstance(input_images, list) else 0,
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
                "capability": "music",
            }
        ),
        "capabilities": {
            "generate": {},
            "edit": {
                "enabled": True,
                "maxInputImages": COMFY_MAX_INPUT_IMAGES,
            },
        },
        "generateMusic": generate_music,
    }
