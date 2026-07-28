import os
import json
import base64
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import resolve_google_api_key_from_environment


@dataclass
class VideoGenerationRequest:
    prompt: str
    model: str = "google/veo-3.0-generate-001"
    number_of_videos: int = 1
    size: Optional[str] = None
    aspect_ratio: Optional[str] = None
    duration_seconds: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        request: Dict[str, Any] = {
            "prompt": self.prompt,
        }

        generation_config: Dict[str, Any] = {
            "numberOfVideos": self.number_of_videos,
        }

        if self.size:
            generation_config["size"] = self.size
        if self.aspect_ratio:
            generation_config["aspectRatio"] = self.aspect_ratio
        if self.duration_seconds:
            generation_config["durationSeconds"] = self.duration_seconds

        request["generationConfig"] = generation_config
        return request


@dataclass
class GeneratedVideo:
    url: Optional[str] = None
    base64_data: Optional[str] = None
    mime_type: str = "video/mp4"
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "base64_data": self.base64_data,
            "mime_type": self.mime_type,
            "duration_seconds": self.duration_seconds,
            "width": self.width,
            "height": self.height,
        }


class GoogleVideoGenerationProvider:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._api_key: Optional[str] = None
        self._base_url: str = "https://generativelanguage.googleapis.com"
        self._model: str = "google/veo-3.0-generate-001"
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
        number_of_videos: int = 1,
        size: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> List[GeneratedVideo]:
        import urllib.request
        import urllib.error

        self.initialize()

        request = VideoGenerationRequest(
            prompt=prompt,
            model=self._model,
            number_of_videos=number_of_videos,
            size=size,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
        )

        model_name = self._model.replace("google/", "")
        url = f"{self._base_url}/v1beta/models/{model_name}:generateVideos"
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
            raise RuntimeError(f"Google Video Generation API error: {e.code} - {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Google Video Generation API connection error: {e.reason}")

    def _parse_response(self, response_data: Dict[str, Any]) -> List[GeneratedVideo]:
        videos = []
        candidates = response_data.get("generatedVideos", [])
        if not candidates:
            candidates = response_data.get("candidates", [])
        if not candidates:
            candidates = [response_data]

        for candidate in candidates:
            video_data = candidate.get("video", {})
            generated = GeneratedVideo()
            generated.url = video_data.get("url")
            generated.base64_data = video_data.get("base64Data")
            generated.mime_type = video_data.get("mimeType", "video/mp4")
            generated.duration_seconds = video_data.get("durationSeconds")
            generated.width = video_data.get("width")
            generated.height = video_data.get("height")
            videos.append(generated)
        return videos

    def get_supported_sizes(self) -> List[str]:
        return ["1280x720", "1920x1080"]

    def get_supported_aspect_ratios(self) -> List[str]:
        return ["16:9", "9:16"]

    def get_max_duration_seconds(self) -> int:
        return 8