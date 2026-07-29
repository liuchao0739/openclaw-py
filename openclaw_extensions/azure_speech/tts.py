import re
import urllib.parse

from .._sdk import (
    assert_ok_or_throw_provider_error,
    fetch_with_ssrf_guard,
    read_provider_json_response,
    read_response_with_limit,
)

DEFAULT_AZURE_SPEECH_VOICE = "en-US-JennyNeural"
DEFAULT_AZURE_SPEECH_LANG = "en-US"
DEFAULT_AZURE_SPEECH_AUDIO_FORMAT = "audio-24khz-48kbitrate-mono-mp3"
DEFAULT_AZURE_SPEECH_VOICE_NOTE_FORMAT = "ogg-24khz-16bit-mono-opus"
DEFAULT_AZURE_SPEECH_TELEPHONY_FORMAT = "raw-8khz-8bit-mono-mulaw"
DEFAULT_AZURE_SPEECH_MAX_BYTES = 16 * 1024 * 1024


def _trim_to_undefined(value):
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return None


def normalize_azure_speech_base_url(params: dict) -> str:
    configured = _trim_to_undefined(params.get("baseUrl")) or _trim_to_undefined(params.get("endpoint"))
    if configured:
        cleaned = re.sub(r"/+$", "", configured)
        cleaned = re.sub(r"/cognitiveservices/v1$", "", cleaned, flags=re.IGNORECASE)
        return cleaned
    region = _trim_to_undefined(params.get("region"))
    if region:
        return f"https://{region}.tts.speech.microsoft.com"
    return None


def _azure_speech_url(params: dict, path: str) -> str:
    base_url = normalize_azure_speech_base_url(params)
    if not base_url:
        raise RuntimeError("Azure Speech region or endpoint missing")
    return f"{base_url}{path}"


def _escape_xml_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_xml_attr(value: str) -> str:
    return _escape_xml_text(value).replace('"', "&quot;").replace("'", "&apos;")


def build_azure_speech_ssml(params: dict) -> str:
    lang = _trim_to_undefined(params.get("lang")) or DEFAULT_AZURE_SPEECH_LANG
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xml:lang="{_escape_xml_attr(lang)}">'
        f'<voice name="{_escape_xml_attr(params["voice"])}">{_escape_xml_text(params["text"])}</voice>'
        f"</speak>"
    )


def infer_azure_speech_file_extension(output_format: str) -> str:
    normalized = output_format.lower()
    if "mp3" in normalized:
        return ".mp3"
    if normalized.startswith("ogg-"):
        return ".ogg"
    if normalized.startswith("webm-"):
        return ".webm"
    if normalized.startswith("riff-"):
        return ".wav"
    if normalized.startswith("raw-"):
        return ".pcm"
    if normalized.startswith("amr-"):
        return ".amr"
    return ".audio"


def is_azure_speech_voice_compatible(output_format: str) -> bool:
    normalized = output_format.lower()
    return normalized.startswith("ogg-") and "opus" in normalized


def _format_voice_description(entry: dict):
    voice_tag = entry.get("VoiceTag") or {}
    if not isinstance(voice_tag, dict):
        voice_tag = {}
    parts = []
    for value in voice_tag.get("TailoredScenarios", []):
        if _trim_to_undefined(value):
            parts.append(value)
    for value in voice_tag.get("VoicePersonalities", []):
        if _trim_to_undefined(value):
            parts.append(value)
    return ", ".join(parts) if parts else None


def _is_deprecated_voice(entry: dict) -> bool:
    if entry.get("IsDeprecated") is True:
        return True
    is_dep = entry.get("IsDeprecated")
    if isinstance(is_dep, str) and is_dep.lower() == "true":
        return True
    status = _trim_to_undefined(entry.get("Status"))
    if status:
        status_lower = status.lower()
        if status_lower in ("deprecated", "retired", "disabled"):
            return True
    return False


async def list_azure_speech_voices(params: dict) -> list:
    url = _azure_speech_url(params, "/cognitiveservices/voices/list")
    hostname = urllib.parse.urlparse(url).hostname
    result = fetch_with_ssrf_guard(
        url=url,
        init={
            "method": "GET",
            "headers": {
                "Ocp-Apim-Subscription-Key": params["apiKey"],
            },
        },
        timeout_ms=params.get("timeoutMs") or 30000,
        policy={"hostnameAllowlist": [hostname]},
        audit_context="azure-speech.voices",
    )
    response = result["response"]
    release = result["release"]

    try:
        assert_ok_or_throw_provider_error(response, "Azure Speech voices API error")
        voices = read_provider_json_response(response, "azure-speech.voices")
        if not isinstance(voices, list):
            return []
        result_voices = []
        for voice in voices:
            if not isinstance(voice, dict) or _is_deprecated_voice(voice):
                continue
            voice_id = _trim_to_undefined(voice.get("ShortName")) or ""
            if not voice_id:
                continue
            voice_tag = voice.get("VoiceTag") or {}
            if not isinstance(voice_tag, dict):
                voice_tag = {}
            personalities = [
                v for v in voice_tag.get("VoicePersonalities", []) if _trim_to_undefined(v)
            ]
            result_voices.append({
                "id": voice_id,
                "name": _trim_to_undefined(voice.get("DisplayName")) or _trim_to_undefined(voice.get("LocalName")),
                "description": _format_voice_description(voice),
                "locale": _trim_to_undefined(voice.get("Locale")),
                "gender": _trim_to_undefined(voice.get("Gender")),
                "personalities": personalities,
            })
        return result_voices
    finally:
        release()


async def azure_speech_tts(params: dict) -> bytes:
    voice = _trim_to_undefined(params.get("voice")) or DEFAULT_AZURE_SPEECH_VOICE
    output_format = _trim_to_undefined(params.get("outputFormat")) or DEFAULT_AZURE_SPEECH_AUDIO_FORMAT
    url = _azure_speech_url(params, "/cognitiveservices/v1")
    hostname = urllib.parse.urlparse(url).hostname
    ssml = build_azure_speech_ssml({
        "text": params["text"],
        "voice": voice,
        "lang": params.get("lang"),
    })
    result = fetch_with_ssrf_guard(
        url=url,
        init={
            "method": "POST",
            "headers": {
                "Content-Type": "application/ssml+xml",
                "Ocp-Apim-Subscription-Key": params["apiKey"],
                "X-Microsoft-OutputFormat": output_format,
                "User-Agent": "OpenClaw",
            },
            "body": ssml,
        },
        timeout_ms=params.get("timeoutMs") or 30000,
        policy={"hostnameAllowlist": [hostname]},
        audit_context="azure-speech.tts",
    )
    response = result["response"]
    release = result["release"]

    try:
        assert_ok_or_throw_provider_error(response, "Azure Speech TTS API error")
        return read_response_with_limit(
            response,
            params.get("maxBytes") or DEFAULT_AZURE_SPEECH_MAX_BYTES,
            on_overflow=lambda ctx: RuntimeError(
                f"Azure Speech TTS audio response exceeds {ctx['maxBytes']} bytes"
            ),
        )
    finally:
        release()
