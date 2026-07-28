import os
import json
import asyncio
import base64
from typing import Optional, Dict, Any, List, Callable, AsyncIterator
from dataclasses import dataclass

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import resolve_google_api_key_from_environment


@dataclass
class RealtimeVoiceConfig:
    model: str = "google/gemini-2.0-flash"
    voice: str = "en-US-Standard-A"
    sample_rate_hz: int = 24000
    encoding: str = "pcm"
    channels: int = 1
    input_audio_mime_type: str = "audio/pcm"
    output_audio_mime_type: str = "audio/pcm"
    temperature: float = 0.7
    max_output_tokens: int = 2048

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "voice": self.voice,
            "sampleRateHz": self.sample_rate_hz,
            "encoding": self.encoding,
            "channels": self.channels,
            "inputAudioMimeType": self.input_audio_mime_type,
            "outputAudioMimeType": self.output_audio_mime_type,
            "temperature": self.temperature,
            "maxOutputTokens": self.max_output_tokens,
        }


@dataclass
class RealtimeVoiceEvent:
    event_type: str
    data: Dict[str, Any]
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class GoogleRealtimeVoiceProvider:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._api_key: Optional[str] = None
        self._base_url: str = "https://generativelanguage.googleapis.com"
        self._ws_url: str = "wss://generativelanguage.googleapis.com/ws"
        self._config = RealtimeVoiceConfig()
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._api_key = resolve_google_api_key_from_environment()
        if self.config and self.config.google_generative_ai_http_base_url:
            self._base_url = self.config.google_generative_ai_http_base_url
        if self.config and self.config.google_api_key:
            self._api_key = self.config.google_api_key
        self._initialized = True

    def set_config(self, config: RealtimeVoiceConfig) -> None:
        self._config = config

    def get_config(self) -> RealtimeVoiceConfig:
        return self._config

    async def connect(self, on_event: Optional[Callable[[RealtimeVoiceEvent], None]] = None) -> str:
        self.initialize()
        session_id = f"session_{os.urandom(16).hex()}"
        return session_id

    async def disconnect(self, session_id: str) -> None:
        pass

    async def send_audio(self, session_id: str, audio_data: bytes) -> None:
        pass

    async def send_text(self, session_id: str, text: str) -> None:
        pass

    async def interrupt(self, session_id: str) -> None:
        pass

    async def set_response_config(
        self,
        session_id: str,
        config: Dict[str, Any],
    ) -> None:
        pass

    async def receive_events(
        self,
        session_id: str,
    ) -> AsyncIterator[RealtimeVoiceEvent]:
        if False:
            yield RealtimeVoiceEvent(event_type="noop", data={})

    def get_supported_voices(self) -> List[str]:
        return [
            "en-US-Standard-A",
            "en-US-Standard-B",
            "en-US-Standard-C",
            "en-US-Excited-A",
            "en-US-Excited-B",
            "en-AU-Standard-A",
            "en-GB-Standard-A",
            "en-GB-Standard-B",
        ]

    def get_supported_configs(self) -> Dict[str, Any]:
        return {
            "sample_rates": [8000, 16000, 24000, 48000],
            "encodings": ["pcm", "opus", "mp3"],
            "channels": [1],
            "input_mime_types": ["audio/pcm", "audio/opus", "audio/mp3"],
            "output_mime_types": ["audio/pcm", "audio/opus", "audio/mp3"],
        }