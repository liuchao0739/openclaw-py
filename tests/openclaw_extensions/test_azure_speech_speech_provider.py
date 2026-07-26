"""Tests for the Azure Speech provider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from openclaw_extensions.azure_speech.speech_provider import build_azure_speech_provider


@pytest.fixture
def provider() -> dict[str, Any]:
    return build_azure_speech_provider()


@pytest.fixture
def env_keys() -> list[str]:
    return [
        "AZURE_SPEECH_KEY",
        "AZURE_SPEECH_API_KEY",
        "AZURE_SPEECH_REGION",
        "AZURE_SPEECH_ENDPOINT",
        "SPEECH_KEY",
        "SPEECH_REGION",
    ]


@pytest.fixture(autouse=True)
def clear_azure_env(monkeypatch: pytest.MonkeyPatch, env_keys: list[str]) -> None:
    for key in env_keys:
        monkeypatch.delenv(key, raising=False)


def test_reports_configured_only_when_key_plus_region_or_endpoint_is_available(
    provider: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert provider["isConfigured"]({"providerConfig": {}, "timeoutMs": 30_000}) is False
    assert (
        provider["isConfigured"]({"providerConfig": {"apiKey": "key"}, "timeoutMs": 30_000})
        is False
    )
    assert (
        provider["isConfigured"](
            {
                "providerConfig": {"apiKey": "key", "region": "eastus"},
                "timeoutMs": 30_000,
            }
        )
        is True
    )

    monkeypatch.setenv("AZURE_SPEECH_KEY", "env-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    assert provider["isConfigured"]({"providerConfig": {}, "timeoutMs": 30_000}) is True


def test_normalizes_provider_owned_config_under_canonical_and_alias_keys(
    provider: dict[str, Any],
) -> None:
    canonical = provider["resolveConfig"](
        {
            "rawConfig": {
                "providers": {
                    "azure-speech": {
                        "apiKey": "key",
                        "region": "eastus",
                        "voice": "en-US-AriaNeural",
                        "lang": "en-US",
                    }
                }
            }
        }
    )
    alias = provider["resolveConfig"](
        {
            "rawConfig": {
                "providers": {
                    "azure": {
                        "apiKey": "alias-key",
                        "endpoint": "https://westus.tts.speech.microsoft.com/cognitiveservices/v1",
                    }
                }
            }
        }
    )

    assert canonical == {
        "apiKey": "key",
        "region": "eastus",
        "endpoint": None,
        "baseUrl": "https://eastus.tts.speech.microsoft.com",
        "voice": "en-US-AriaNeural",
        "lang": "en-US",
        "outputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "voiceNoteOutputFormat": "ogg-24khz-16bit-mono-opus",
        "timeoutMs": None,
    }
    assert alias == {
        "apiKey": "alias-key",
        "region": None,
        "endpoint": "https://westus.tts.speech.microsoft.com/cognitiveservices/v1",
        "baseUrl": "https://westus.tts.speech.microsoft.com",
        "voice": "en-US-JennyNeural",
        "lang": "en-US",
        "outputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "voiceNoteOutputFormat": "ogg-24khz-16bit-mono-opus",
        "timeoutMs": None,
    }


def test_parses_provider_specific_tts_directives(provider: dict[str, Any]) -> None:
    policy = {
        "enabled": True,
        "allowText": True,
        "allowProvider": True,
        "allowVoice": True,
        "allowModelId": True,
        "allowVoiceSettings": True,
        "allowNormalization": True,
        "allowSeed": True,
    }

    assert provider["parseDirectiveToken"](
        {"key": "azure_voice", "value": "v", "policy": policy}
    ) == {
        "handled": True,
        "overrides": {"voice": "v"},
    }
    assert provider["parseDirectiveToken"](
        {"key": "azure_lang", "value": "en-US", "policy": policy}
    ) == {
        "handled": True,
        "overrides": {"lang": "en-US"},
    }
    assert provider["parseDirectiveToken"](
        {"key": "azure_output_format", "value": "ogg", "policy": policy}
    ) == {
        "handled": True,
        "overrides": {"outputFormat": "ogg"},
    }


@pytest.mark.asyncio
async def test_uses_native_ogg_opus_for_voice_note_output(
    provider: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    azure_speech_tts_mock = AsyncMock(return_value=b"audio-bytes")
    monkeypatch.setattr(
        "openclaw_extensions.azure_speech.speech_provider.azure_speech_tts",
        azure_speech_tts_mock,
    )

    result = await provider["synthesize"](
        {
            "text": "hello",
            "cfg": {},
            "providerConfig": {
                "apiKey": "key",
                "region": "eastus",
                "voice": "en-US-JennyNeural",
            },
            "providerOverrides": {
                "voice": "en-US-AriaNeural",
                "lang": "en-US",
            },
            "target": "voice-note",
            "timeoutMs": 30_000,
        }
    )

    azure_speech_tts_mock.assert_awaited_once_with(
        text="hello",
        api_key="key",
        base_url="https://eastus.tts.speech.microsoft.com",
        endpoint=None,
        region="eastus",
        voice="en-US-AriaNeural",
        lang="en-US",
        output_format="ogg-24khz-16bit-mono-opus",
        timeout_ms=30_000,
        max_bytes=16 * 1024 * 1024,
    )
    assert result == {
        "audioBuffer": b"audio-bytes",
        "outputFormat": "ogg-24khz-16bit-mono-opus",
        "fileExtension": ".ogg",
        "voiceCompatible": True,
    }


@pytest.mark.asyncio
async def test_honors_voice_and_language_overrides_for_telephony_output(
    provider: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    azure_speech_tts_mock = AsyncMock(return_value=b"audio-bytes")
    monkeypatch.setattr(
        "openclaw_extensions.azure_speech.speech_provider.azure_speech_tts",
        azure_speech_tts_mock,
    )

    result = await provider["synthesizeTelephony"](
        {
            "text": "hello",
            "cfg": {},
            "providerConfig": {
                "apiKey": "key",
                "region": "eastus",
                "voice": "en-US-JennyNeural",
                "lang": "en-US",
            },
            "providerOverrides": {
                "voice": "en-US-AriaNeural",
                "lang": "es-US",
            },
            "timeoutMs": 30_000,
        }
    )

    azure_speech_tts_mock.assert_awaited_once_with(
        text="hello",
        api_key="key",
        base_url="https://eastus.tts.speech.microsoft.com",
        endpoint=None,
        region="eastus",
        voice="en-US-AriaNeural",
        lang="es-US",
        output_format="raw-8khz-8bit-mono-mulaw",
        timeout_ms=30_000,
        max_bytes=16 * 1024 * 1024,
    )
    assert result == {
        "audioBuffer": b"audio-bytes",
        "outputFormat": "raw-8khz-8bit-mono-mulaw",
        "sampleRate": 8_000,
    }


@pytest.mark.asyncio
async def test_applies_the_configured_media_byte_cap_to_synthesis_requests(
    provider: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    azure_speech_tts_mock = AsyncMock(return_value=b"audio-bytes")
    monkeypatch.setattr(
        "openclaw_extensions.azure_speech.speech_provider.azure_speech_tts",
        azure_speech_tts_mock,
    )

    await provider["synthesize"](
        {
            "text": "hello",
            "cfg": {"agents": {"defaults": {"mediaMaxMb": 2}}},
            "providerConfig": {
                "apiKey": "key",
                "region": "eastus",
                "voice": "en-US-JennyNeural",
            },
            "target": "audio-file",
            "timeoutMs": 30_000,
        }
    )

    assert azure_speech_tts_mock.await_args is not None
    assert azure_speech_tts_mock.await_args.kwargs["max_bytes"] == 2 * 1024 * 1024


@pytest.mark.asyncio
async def test_lists_voices_through_config_or_explicit_request_auth(
    provider: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    list_azure_speech_voices_mock = AsyncMock(
        return_value=[{"id": "en-US-JennyNeural", "name": "Jenny"}]
    )
    monkeypatch.setattr(
        "openclaw_extensions.azure_speech.speech_provider.list_azure_speech_voices",
        list_azure_speech_voices_mock,
    )

    voices = await provider["listVoices"]({"providerConfig": {"apiKey": "key", "region": "eastus"}})

    assert voices == [{"id": "en-US-JennyNeural", "name": "Jenny"}]
    list_azure_speech_voices_mock.assert_awaited_once_with(
        api_key="key",
        base_url="https://eastus.tts.speech.microsoft.com",
        endpoint=None,
        region="eastus",
        timeout_ms=None,
    )
