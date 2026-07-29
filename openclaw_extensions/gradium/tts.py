import json
import urllib.parse

from .._sdk import assert_ok_or_throw_provider_error, fetch_with_ssrf_guard, read_response_with_limit
from .shared import normalize_gradium_base_url

DEFAULT_TTS_MAX_BYTES = 16 * 1024 * 1024

VALID_OUTPUT_FORMATS = ("wav", "opus", "ulaw_8000", "pcm", "pcm_24000", "alaw_8000")


async def gradium_tts(*, text, api_key, base_url, voice_id, output_format, timeout_ms, max_bytes=None):
    if max_bytes is None:
        max_bytes = DEFAULT_TTS_MAX_BYTES
    normalized_base_url = normalize_gradium_base_url(base_url)
    url = f"{normalized_base_url}/api/post/speech/tts"
    hostname = urllib.parse.urlparse(normalized_base_url).hostname

    body = json.dumps({
        "text": text,
        "voice_id": voice_id,
        "only_audio": True,
        "output_format": output_format,
        "json_config": json.dumps({"padding_bonus": 0}),
    })

    result = fetch_with_ssrf_guard(
        url=url,
        init={
            "method": "POST",
            "headers": {
                "x-api-key": api_key,
                "Content-Type": "application/json",
            },
            "body": body,
        },
        timeout_ms=timeout_ms,
        policy={"hostnameAllowlist": [hostname]},
        audit_context="gradium.tts",
    )
    response = result["response"]
    release = result["release"]

    try:
        assert_ok_or_throw_provider_error(response, "Gradium API error")
        return read_response_with_limit(
            response,
            max_bytes,
            on_overflow=lambda ctx: RuntimeError(
                f"Gradium TTS audio response exceeds {ctx['maxBytes']} bytes"
            ),
        )
    finally:
        release()
