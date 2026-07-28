import os
import json
import base64
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import resolve_google_api_key_from_environment


@dataclass
class SpeechRequest:
    prompt: str
    model: str = "google/gemini-2.0-flash"
    voice: str = "en-US-Standard-A"
    audio_config: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        request: Dict[str, Any] = {
            "contents": [{"text": self.prompt}],
        }
        if self.audio_config:
            request["audioConfig"] = self.audio_config
        else:
            request["audioConfig"] = {
                "voice": {"languageCode": self.voice},
                "config": {"audioEncoding": "MP3"},
            }
        return request


@dataclass
class SpeechResult:
    audio_data: Optional[str] = None
    mime_type: str = "audio/mpeg"
    duration_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audio_data": self.audio_data,
            "mime_type": self.mime_type,
            "duration_seconds": self.duration_seconds,
        }


class GoogleSpeechProvider:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._api_key: Optional[str] = None
        self._base_url: str = "https://generativelanguage.googleapis.com"
        self._model: str = "google/gemini-2.0-flash"
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

    def set_model(self, model: str) -> None:
        self._model = model

    def synthesize(
        self,
        text: str,
        voice: str = "en-US-Standard-A",
        audio_encoding: str = "MP3",
    ) -> SpeechResult:
        import urllib.request
        import urllib.error

        self.initialize()

        request = SpeechRequest(
            prompt=text,
            model=self._model,
            voice=voice,
            audio_config={
                "voice": {"languageCode": voice},
                "config": {"audioEncoding": audio_encoding},
            },
        )

        model_name = self._model.replace("google/", "")
        url = f"{self._base_url}/v1beta/models/{model_name}:generateContent"
        if self._api_key:
            url += f"?key={self._api_key}"

        data = json.dumps(request.to_dict()).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                return self._parse_response(response_data)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"Google Speech API error: {e.code} - {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Google Speech API connection error: {e.reason}")

    def _parse_response(self, response_data: Dict[str, Any]) -> SpeechResult:
        candidates = response_data.get("candidates", [])
        if not candidates:
            return SpeechResult()

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])

        for part in parts:
            if "inlineData" in part:
                inline = part["inlineData"]
                return SpeechResult(
                    audio_data=inline.get("data"),
                    mime_type=inline.get("mimeType", "audio/mpeg"),
                )

        return SpeechResult()

    def list_available_voices(self) -> List[str]:
        return [
            "en-US-Standard-A",
            "en-US-Standard-B",
            "en-US-Standard-C",
            "en-US-Standard-D",
            "en-US-Standard-E",
            "en-US-Excited-A",
            "en-US-Excited-B",
            "en-US-Shopper-A",
            "en-US-Shopper-B",
            "en-US-USCinematic-A",
            "en-US-USCinematic-B",
            "en-AU-Standard-A",
            "en-AU-Standard-B",
            "en-GB-Standard-A",
            "en-GB-Standard-B",
            "en-GB-Standard-C",
        ]

    def list_supported_encodings(self) -> List[str]:
        return ["MP3", "LINEAR16", "OGG_OPUS", "MULAW"]