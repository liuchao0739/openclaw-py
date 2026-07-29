import urllib.parse
from typing import Any, Optional

from .._sdk import (
    assert_ok_or_throw_provider_error,
    fetch_with_ssrf_guard,
    read_provider_json_response,
)

DEFAULT_DEEPGRAM_AUDIO_BASE_URL = "https://api.deepgram.com/v1"
DEFAULT_DEEPGRAM_AUDIO_MODEL = "nova-3"


def _resolve_model(model: Any) -> str:
    if isinstance(model, str):
        trimmed = model.strip()
        if trimmed:
            return trimmed
    return DEFAULT_DEEPGRAM_AUDIO_MODEL


def _as_record(value: Any) -> Optional[dict]:
    if isinstance(value, dict):
        return value
    return None


def _read_deepgram_transcript(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    results = _as_record(payload.get("results"))
    if not results:
        return None
    channels = results.get("channels")
    if not isinstance(channels, list) or not channels:
        raise RuntimeError("Audio transcription failed: malformed JSON response")
    channel = _as_record(channels[0]) if channels else None
    if not channel:
        return None
    alternatives = channel.get("alternatives")
    if not isinstance(alternatives, list) or not alternatives:
        raise RuntimeError("Audio transcription failed: malformed JSON response")
    alternative = _as_record(alternatives[0]) if alternatives else None
    if not alternative:
        return None
    transcript = alternative.get("transcript")
    if transcript is not None and not isinstance(transcript, str):
        raise RuntimeError("Audio transcription failed: malformed JSON response")
    return transcript


async def transcribe_deepgram_audio(params: dict) -> dict:
    model = _resolve_model(params.get("model"))
    base_url = params.get("baseUrl") or DEFAULT_DEEPGRAM_AUDIO_BASE_URL
    mime = params.get("mime") or "application/octet-stream"
    headers = {
        "authorization": f"Token {params['apiKey']}",
        "content-type": mime,
    }
    request_headers = params.get("headers")
    if isinstance(request_headers, dict):
        headers.update(request_headers)

    base = str(base_url).rstrip("/")
    url = f"{base}/listen"
    query_parts = [("model", model)]
    language = params.get("language")
    if isinstance(language, str) and language.strip():
        query_parts.append(("language", language.strip()))
    query = params.get("query")
    if isinstance(query, dict):
        for key, value in query.items():
            if value is None:
                continue
            query_parts.append((key, str(value)))
    query_string = urllib.parse.urlencode(query_parts)
    if query_string:
        url = f"{url}?{query_string}"

    raw_buffer = params["buffer"]
    if isinstance(raw_buffer, (bytes, bytearray)):
        body = bytes(raw_buffer)
    else:
        body = bytes(raw_buffer)

    result = fetch_with_ssrf_guard(
        url=url,
        init={
            "method": "POST",
            "headers": headers,
            "body": body,
        },
        timeout_ms=params.get("timeoutMs") or 30000,
        audit_context="deepgram.audio",
    )
    response = result["response"]
    release = result["release"]
    try:
        assert_ok_or_throw_provider_error(response, "Audio transcription failed")
        payload = read_provider_json_response(response, "Audio transcription failed")
        transcript = _read_deepgram_transcript(payload)
        if not transcript:
            raise RuntimeError("Audio transcription response missing transcript")
        return {"text": transcript, "model": model}
    finally:
        release()
