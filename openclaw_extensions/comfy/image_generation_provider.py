"""Comfy image generation provider."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.comfy.workflow_runtime import (
    DEFAULT_COMFY_MODEL,
    is_comfy_capability_configured,
    run_comfy_workflow,
    set_comfy_fetch_guard_for_testing,
)

__all__ = [
    "build_comfy_image_generation_provider",
    "set_comfy_fetch_guard_for_testing",
]


def build_comfy_image_generation_provider() -> dict[str, Any]:
    async def generate_image(req: dict[str, Any]) -> dict[str, Any]:
        input_images = req.get("inputImages")
        if isinstance(input_images, list) and len(input_images) > 1:
            raise RuntimeError(
                "Comfy image generation currently supports at most one reference image",
            )
        input_image = input_images[0] if isinstance(input_images, list) and input_images else None
        result = await run_comfy_workflow(
            {
                "cfg": req["cfg"],
                "agentDir": req.get("agentDir"),
                "authStore": req.get("authStore"),
                "prompt": req["prompt"],
                "model": req.get("model"),
                "timeoutMs": req.get("timeoutMs"),
                "capability": "image",
                "outputKinds": ["images"],
                "inputImage": input_image,
            }
        )
        images = [
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
            "images": images,
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
                "capability": "image",
            }
        ),
        "capabilities": {
            "generate": {
                "maxCount": 1,
                "supportsSize": False,
                "supportsAspectRatio": False,
                "supportsResolution": False,
            },
            "edit": {
                "enabled": True,
                "maxCount": 1,
                "maxInputImages": 1,
                "supportsSize": False,
                "supportsAspectRatio": False,
                "supportsResolution": False,
            },
        },
        "generateImage": generate_image,
    }
