import os
import json
import base64
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import resolve_google_api_key_from_environment


@dataclass
class MusicGenerationRequest:
    prompt: str
    model: str = "google/audio-2.0-generate-001"
    number_of_tracks: int = 1
    duration_seconds: Optional[int] = None
    lyrics: Optional[str] = None
    style: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        request: Dict[str, Any] = {
            "prompt": self.prompt,
        }

        generation_config: Dict[str, Any] = {
            "numberOfTracks": self.number_of_tracks,
        }

        if self.duration_seconds:
            generation_config["durationSeconds"] = self.duration_seconds
        if self.style:
            generation_config["style"] = self.style

        request["generationConfig"] = generation_config

        if self.lyrics:
            request["lyrics"] = self.lyrics

        return request


@dataclass
class GeneratedMusic:
    url: Optional[str] = None
    base64_data: Optional[str] = None
    mime_type: str = "audio/mpeg"
    duration_seconds: Optional[float] = None
    title: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "base64_data": self.base64_data,
            "mime_type": self.mime_type,
            "duration_seconds": self.duration_seconds,
            "title": self.title,
        }


class GoogleMusicGenerationProvider:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._api_key: Optional[str] = None
        self._base_url: str = "https://generativelanguage.googleapis.com"
        self._model: str = "google/audio-2.0-generate-001"
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

    def generate(
        self,
        prompt: str,
        number_of_tracks: int = 1,
        duration_seconds: Optional[int] = None,
        lyrics: Optional[str] = None,
        style: Optional[str] = None,
    ) -> List[GeneratedMusic]:
        import urllib.request
        import urllib.error

        self.initialize()

        request = MusicGenerationRequest(
            prompt=prompt,
            model=self._model,
            number_of_tracks=number_of_tracks,
            duration_seconds=duration_seconds,
            lyrics=lyrics,
            style=style,
        )

        model_name = self._model.replace("google/", "")
        url = f"{self._base_url}/v1beta/models/{model_name}:generateAudio"
        if self._api_key:
            url += f"?key={self._api_key}"

        data = json.dumps(request.to_dict()).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                return self._parse_response(response_data)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"Google Music Generation API error: {e.code} - {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Google Music Generation API connection error: {e.reason}")

    def _parse_response(self, response_data: Dict[str, Any]) -> List[GeneratedMusic]:
        tracks = []
        candidates = response_data.get("generatedAudio", [])
        if not candidates:
            candidates = response_data.get("candidates", [])
        if not candidates:
            candidates = [response_data]

        for candidate in candidates:
            audio_data = candidate.get("audio", {})
            generated = GeneratedMusic()
            generated.url = audio_data.get("url")
            generated.base64_data = audio_data.get("base64Data")
            generated.mime_type = audio_data.get("mimeType", "audio/mpeg")
            generated.duration_seconds = audio_data.get("durationSeconds")
            generated.title = candidate.get("title")
            tracks.append(generated)
        return tracks

    def get_max_duration_seconds(self) -> int:
        return 30

    def get_supported_styles(self) -> List[str]:
        return [
            "pop",
            "rock",
            "electronic",
            "classical",
            "jazz",
            "hip-hop",
            "folk",
            "ambient",
            "cinematic",
        ]