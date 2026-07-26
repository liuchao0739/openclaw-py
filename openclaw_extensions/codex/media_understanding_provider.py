"""Codex-backed media understanding provider."""

from __future__ import annotations

import base64
import json
from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw_extensions.codex.provider_catalog import CODEX_PROVIDER_ID, FALLBACK_CODEX_MODELS
from openclaw_extensions.codex.src.app_server.bounded_turn import run_bounded_codex_app_server_turn

DEFAULT_CODEX_IMAGE_MODEL = next(
    (model["id"] for model in FALLBACK_CODEX_MODELS if "image" in model.get("inputModalities", [])),
    FALLBACK_CODEX_MODELS[0]["id"] if FALLBACK_CODEX_MODELS else None,
)
DEFAULT_CODEX_IMAGE_PROMPT = "Describe the image."


def build_codex_media_understanding_provider(options: dict[str, Any] | None = None) -> dict[str, Any]:
    options = options or {}

    async def describe_image(req: dict[str, Any]) -> dict[str, Any]:
        return await _describe_codex_images(
            {
                "images": [
                    {
                        "buffer": req["buffer"],
                        "fileName": req.get("fileName"),
                        "mime": req.get("mime"),
                    }
                ],
                "provider": req.get("provider"),
                "model": req["model"],
                "prompt": req.get("prompt"),
                "maxTokens": req.get("maxTokens"),
                "timeoutMs": req["timeoutMs"],
                "profile": req.get("profile"),
                "preferredProfile": req.get("preferredProfile"),
                "authStore": req.get("authStore"),
                "agentDir": req.get("agentDir"),
                "cfg": req.get("cfg"),
            },
            options,
        )

    provider: dict[str, Any] = {
        "id": CODEX_PROVIDER_ID,
        "capabilities": ["image"],
        "describeImage": describe_image,
        "describeImages": lambda req: _describe_codex_images(req, options),
        "extractStructured": lambda req: _extract_codex_structured(req, options),
    }
    if DEFAULT_CODEX_IMAGE_MODEL:
        provider["defaultModels"] = {"image": DEFAULT_CODEX_IMAGE_MODEL}
    return provider


async def _describe_codex_images(req: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    model = str(req.get("model") or "").strip()
    if not model:
        raise ValueError("Codex image understanding requires model id.")
    text_result = await run_bounded_codex_app_server_turn(
        {
            "config": req.get("cfg"),
            "model": {"mode": "required", "id": model},
            "profile": req.get("profile"),
            "timeoutMs": req.get("timeoutMs"),
            "agentDir": req.get("agentDir"),
            "authProfileStore": req.get("authStore"),
            "options": options,
            "taskLabel": "image understanding",
            "developerInstructions": (
                "You are OpenClaw's bounded image-understanding worker. Describe only the provided "
                "image content. Do not call tools, edit files, or ask follow-up questions."
            ),
            "input": [
                {"type": "text", "text": _build_codex_image_prompt(req), "text_elements": []},
                *[
                    {
                        "type": "image",
                        "url": f"data:{image.get('mime') or 'image/png'};base64,"
                        f"{_encode_buffer(image.get('buffer'))}",
                    }
                    for image in req.get("images") or []
                ],
            ],
            "requiredModalities": ["text", "image"],
            "isolation": "configured-transport",
        }
    )
    return {"text": text_result["text"], "model": model}


def _encode_buffer(buffer: Any) -> str:
    if isinstance(buffer, (bytes, bytearray)):
        return base64.b64encode(buffer).decode("ascii")
    return base64.b64encode(str(buffer).encode("utf-8")).decode("ascii")


def _build_codex_image_prompt(req: dict[str, Any]) -> str:
    prompt = str(req.get("prompt") or "").strip() or DEFAULT_CODEX_IMAGE_PROMPT
    images = req.get("images") or []
    if len(images) <= 1:
        return prompt
    return f"{prompt}\n\nAnalyze all {len(images)} images together."


async def _extract_codex_structured(req: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    model = str(req.get("model") or "").strip()
    if not model:
        raise ValueError("Codex structured extraction requires model id.")
    instructions = str(req.get("instructions") or "").strip()
    if not instructions:
        raise ValueError("Codex structured extraction requires instructions.")
    if not req.get("input"):
        raise ValueError("Codex structured extraction requires at least one input.")
    if not any(entry.get("type") == "image" for entry in req.get("input") or []):
        raise ValueError("Codex structured extraction requires at least one image input.")
    text_result = await run_bounded_codex_app_server_turn(
        {
            "config": req.get("cfg"),
            "model": {"mode": "required", "id": model},
            "profile": req.get("profile"),
            "timeoutMs": req.get("timeoutMs"),
            "agentDir": req.get("agentDir"),
            "authProfileStore": req.get("authStore"),
            "options": options,
            "taskLabel": "structured extraction",
            "developerInstructions": (
                "You are OpenClaw's bounded structured-extraction worker. Return only the requested "
                "extraction. Do not call tools, edit files, ask follow-up questions, or include secrets."
            ),
            "input": _build_codex_structured_input(req),
            "requiredModalities": ["text", "image"],
            "isolation": "configured-transport",
        }
    )
    return _normalize_structured_extraction_result(
        {
            "text": text_result["text"],
            "model": model,
            "provider": req.get("provider"),
            "req": req,
        }
    )


def _build_codex_structured_input(req: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"type": "text", "text": _build_structured_extraction_prompt(req), "text_elements": []},
        *[
            (
                {"type": "text", "text": entry["text"], "text_elements": []}
                if entry.get("type") == "text"
                else {
                    "type": "image",
                    "url": f"data:{entry.get('mime') or 'image/png'};base64,{_encode_buffer(entry.get('buffer'))}",
                }
            )
            for entry in req.get("input") or []
        ],
    ]


def _build_structured_extraction_prompt(req: dict[str, Any]) -> str:
    parts = [
        str(req.get("instructions") or "").strip(),
        f"Schema name: {req['schemaName']}" if req.get("schemaName") else None,
        f"JSON schema:\n{json.dumps(req['jsonSchema'])}" if req.get("jsonSchema") else None,
        (
            "Return the extraction as concise text."
            if req.get("jsonMode") is False
            else "Return valid JSON only. Do not wrap the JSON in Markdown fences."
        ),
    ]
    return "\n\n".join(part for part in parts if part)


def _normalize_structured_extraction_result(params: dict[str, Any]) -> dict[str, Any]:
    req = params["req"]
    result: dict[str, Any] = {
        "text": params["text"],
        "model": params["model"],
        "provider": params["provider"],
        "contentType": "text" if req.get("jsonMode") is False else "json",
    }
    if req.get("jsonMode") is False:
        return result
    try:
        result["parsed"] = json.loads(params["text"])
    except json.JSONDecodeError as exc:
        raise ValueError("Codex structured extraction returned invalid JSON.") from exc
    json_schema = req.get("jsonSchema")
    if is_record(json_schema) and result["parsed"] is not None:
        result["parsed"] = result["parsed"]
    return result
