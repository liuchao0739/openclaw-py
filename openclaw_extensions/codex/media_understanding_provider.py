import base64
import json
from typing import Any, Optional

from openclaw.plugin_sdk.json_schema_runtime import validate_json_schema_value

from .provider_catalog import CODEX_PROVIDER_ID, FALLBACK_CODEX_MODELS

DEFAULT_CODEX_IMAGE_MODEL = next(
    (model["id"] for model in FALLBACK_CODEX_MODELS if "image" in model.get("inputModalities", [])),
    FALLBACK_CODEX_MODELS[0]["id"] if FALLBACK_CODEX_MODELS else None,
)
DEFAULT_CODEX_IMAGE_PROMPT = "Describe the image."


def build_codex_media_understanding_provider(options: Optional[dict] = None) -> dict:
    options = options or {}
    provider = {
        "id": CODEX_PROVIDER_ID,
        "capabilities": ["image"],
    }
    if DEFAULT_CODEX_IMAGE_MODEL:
        provider["defaultModels"] = {"image": DEFAULT_CODEX_IMAGE_MODEL}

    async def _describe_image(req):
        return await _describe_codex_images({
            "images": [
                {
                    "buffer": req["buffer"],
                    "fileName": req.get("fileName"),
                    "mime": req.get("mime"),
                }
            ],
            "provider": req["provider"],
            "model": req["model"],
            "prompt": req.get("prompt"),
            "maxTokens": req.get("maxTokens"),
            "timeoutMs": req.get("timeoutMs"),
            "profile": req.get("profile"),
            "preferredProfile": req.get("preferredProfile"),
            "authStore": req.get("authStore"),
            "agentDir": req.get("agentDir"),
            "cfg": req.get("cfg"),
        }, options)

    async def _describe_images(req):
        return await _describe_codex_images(req, options)

    async def _extract_structured(req):
        return await _extract_codex_structured(req, options)

    provider["describeImage"] = _describe_image
    provider["describeImages"] = _describe_images
    provider["extractStructured"] = _extract_structured
    return provider


async def _describe_codex_images(req: dict, options: dict) -> dict:
    model = (req.get("model") or "").strip()
    if not model:
        raise Error("Codex image understanding requires model id.")

    from .src.app_server.bounded_turn import run_bounded_codex_app_server_turn

    image_input = []
    for image in req.get("images", []):
        buffer = image["buffer"]
        if isinstance(buffer, str):
            buffer_bytes = buffer.encode("utf-8")
        else:
            buffer_bytes = buffer
        mime = image.get("mime") or "image/png"
        data_url = f"data:{mime};base64,{base64.b64encode(buffer_bytes).decode('ascii')}"
        image_input.append({"type": "image", "url": data_url})

    result = await run_bounded_codex_app_server_turn({
        "config": req.get("cfg"),
        "model": {"mode": "required", "id": model},
        "profile": req.get("profile"),
        "timeoutMs": req.get("timeoutMs"),
        "agentDir": req.get("agentDir"),
        "authProfileStore": req.get("authStore"),
        "options": options,
        "taskLabel": "image understanding",
        "developerInstructions": "You are OpenClaw's bounded image-understanding worker. Describe only the provided image content. Do not call tools, edit files, or ask follow-up questions.",
        "input": [
            {"type": "text", "text": _build_codex_image_prompt(req), "text_elements": []},
            *image_input,
        ],
        "requiredModalities": ["text", "image"],
        "isolation": "configured-transport",
    })
    return {"text": result["text"], "model": model}


async def _extract_codex_structured(req: dict, options: dict) -> dict:
    model = (req.get("model") or "").strip()
    if not model:
        raise Error("Codex structured extraction requires model id.")
    instructions = (req.get("instructions") or "").strip()
    if not instructions:
        raise Error("Codex structured extraction requires instructions.")
    if not req.get("input"):
        raise Error("Codex structured extraction requires at least one input.")
    if not any(entry.get("type") == "image" for entry in req["input"]):
        raise Error("Codex structured extraction requires at least one image input.")

    from .src.app_server.bounded_turn import run_bounded_codex_app_server_turn

    result = await run_bounded_codex_app_server_turn({
        "config": req.get("cfg"),
        "model": {"mode": "required", "id": model},
        "profile": req.get("profile"),
        "timeoutMs": req.get("timeoutMs"),
        "agentDir": req.get("agentDir"),
        "authProfileStore": req.get("authStore"),
        "options": options,
        "taskLabel": "structured extraction",
        "developerInstructions": "You are OpenClaw's bounded structured-extraction worker. Return only the requested extraction. Do not call tools, edit files, ask follow-up questions, or include secrets.",
        "input": _build_codex_structured_input(req),
        "requiredModalities": _required_structured_modalities(),
        "isolation": "configured-transport",
    })
    return _normalize_structured_extraction_result({
        "text": result["text"],
        "model": model,
        "provider": req["provider"],
        "req": req,
    })


def _build_codex_image_prompt(req: dict) -> str:
    prompt = (req.get("prompt") or "").strip() or DEFAULT_CODEX_IMAGE_PROMPT
    images = req.get("images", [])
    if len(images) <= 1:
        return prompt
    return f"{prompt}\n\nAnalyze all {len(images)} images together."


def _required_structured_modalities() -> list:
    return ["text", "image"]


def _build_codex_structured_input(req: dict) -> list:
    items = [{"type": "text", "text": _build_structured_extraction_prompt(req), "text_elements": []}]
    for entry in req.get("input", []):
        if entry["type"] == "text":
            items.append({"type": "text", "text": entry["text"], "text_elements": []})
        else:
            buffer = entry["buffer"]
            if isinstance(buffer, str):
                buffer_bytes = buffer.encode("utf-8")
            else:
                buffer_bytes = buffer
            mime = entry.get("mime") or "image/png"
            data_url = f"data:{mime};base64,{base64.b64encode(buffer_bytes).decode('ascii')}"
            items.append({"type": "image", "url": data_url})
    return items


def _build_structured_extraction_prompt(req: dict) -> str:
    parts = [(req.get("instructions") or "").strip()]
    if req.get("schemaName"):
        parts.append(f"Schema name: {req['schemaName']}")
    if req.get("jsonSchema"):
        parts.append(f"JSON schema:\n{json.dumps(req['jsonSchema'])}")
    if req.get("jsonMode") is False:
        parts.append("Return the extraction as concise text.")
    else:
        parts.append("Return valid JSON only. Do not wrap the JSON in Markdown fences.")
    return "\n\n".join(part for part in parts if part)


def _is_json_schema_object(value: Any) -> bool:
    return isinstance(value, dict) and value is not None and not isinstance(value, list)


def _normalize_structured_extraction_result(params: dict) -> dict:
    req = params["req"]
    result = {
        "text": params["text"],
        "model": params["model"],
        "provider": params["provider"],
        "contentType": "text" if req.get("jsonMode") is False else "json",
    }
    if req.get("jsonMode") is not False:
        try:
            result["parsed"] = json.loads(params["text"])
        except ValueError:
            raise Error("Codex structured extraction returned invalid JSON.")
        if _is_json_schema_object(req.get("jsonSchema")):
            validation = validate_json_schema_value({
                "schema": req["jsonSchema"],
                "cacheKey": "codex.media-understanding.extractStructured",
                "value": result["parsed"],
                "cache": False,
            })
            if not validation["ok"]:
                message = "; ".join(error["text"] for error in validation["errors"]) or "invalid"
                raise Error(f"Codex structured extraction JSON did not match schema: {message}")
            result["parsed"] = validation["value"]
    return result


class Error(Exception):
    pass
