"""Elevenlabs provider module implements model/runtime integration."""

from __future__ import annotations

import os
from typing import Any

from openclaw.plugin_sdk.media_understanding import (
    build_audio_transcription_form_data,
    post_transcription_request,
    read_provider_json_object_response,
    require_transcription_text,
)
from openclaw.plugin_sdk.provider_http import (
    assert_ok_or_throw_http_error,
    resolve_provider_http_request_config,
)
from openclaw_extensions.elevenlabs.shared import (
    DEFAULT_ELEVENLABS_BASE_URL,
    normalize_elevenlabs_base_url,
)

DEFAULT_ELEVENLABS_STT_MODEL = "scribe_v2"


async def transcribe_eleven_labs_audio(req: dict[str, Any]) -> dict[str, str]:
    api_key = (
        req.get("apiKey")
        or os.environ.get("ELEVENLABS_API_KEY")
        or os.environ.get("XI_API_KEY")
    )
    if not api_key:
        raise RuntimeError("ElevenLabs API key missing")

    model_raw = req.get("model")
    model = model_raw.strip() if isinstance(model_raw, str) and model_raw.strip() else DEFAULT_ELEVENLABS_STT_MODEL
    request_config = resolve_provider_http_request_config(
        {
            "baseUrl": normalize_elevenlabs_base_url(req.get("baseUrl")),
            "defaultBaseUrl": DEFAULT_ELEVENLABS_BASE_URL,
            "headers": req.get("headers"),
            "request": req.get("request"),
            "defaultHeaders": {
                "xi-api-key": api_key,
            },
            "provider": "elevenlabs",
            "api": "elevenlabs-speech-to-text",
            "capability": "audio",
            "transport": "media-understanding",
        }
    )
    multipart = build_audio_transcription_form_data(
        {
            "buffer": req["buffer"],
            "fileName": req.get("fileName"),
            "mime": req.get("mime"),
            "fields": {
                "model_id": model,
                "language_code": req.get("language"),
                "prompt": req.get("prompt"),
            },
        }
    )
    result = await post_transcription_request(
        {
            "url": f"{request_config['baseUrl']}/v1/speech-to-text",
            "headers": request_config["headers"],
            "multipart": multipart,
            "timeoutMs": req.get("timeoutMs"),
            "fetchFn": req.get("fetchFn"),
        }
    )
    response = result["response"]
    release = result["release"]
    try:
        await assert_ok_or_throw_http_error(response, "ElevenLabs audio transcription failed")
        payload = await read_provider_json_object_response(
            response,
            "ElevenLabs audio transcription failed",
        )
        text_value = payload.get("text")
        text = require_transcription_text(
            text_value if isinstance(text_value, str) else None,
            "ElevenLabs audio transcription response missing text",
        )
        return {"text": text, "model": model}
    finally:
        await release()


eleven_labs_media_understanding_provider: dict[str, Any] = {
    "id": "elevenlabs",
    "capabilities": ["audio"],
    "defaultModels": {"audio": DEFAULT_ELEVENLABS_STT_MODEL},
    "autoPriority": {"audio": 45},
    "transcribeAudio": transcribe_eleven_labs_audio,
}
