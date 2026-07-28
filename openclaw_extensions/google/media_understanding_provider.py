import os
import json
import base64
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import resolve_google_api_key_from_environment


@dataclass
class MediaUnderstandingRequest:
    content: str
    mime_type: str
    prompt: str
    model: str = "google/gemini-2.5-pro"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contents": [
                {
                    "parts": [
                        {"inline_data": {"mime_type": self.mime_type, "data": self.content}},
                        {"text": self.prompt},
                    ]
                }
            ]
        }


@dataclass
class MediaUnderstandingResult:
    description: str
    labels: List[str]
    objects: List[Dict[str, Any]]
    text_content: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "labels": self.labels,
            "objects": self.objects,
            "text_content": self.text_content,
        }


class GoogleMediaUnderstandingProvider:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._api_key: Optional[str] = None
        self._base_url: str = "https://generativelanguage.googleapis.com"
        self._model: str = "google/gemini-2.5-pro"
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

    def understand(
        self,
        content: str,
        mime_type: str,
        prompt: str = "Describe this media in detail.",
    ) -> MediaUnderstandingResult:
        import urllib.request
        import urllib.error

        self.initialize()

        request = MediaUnderstandingRequest(
            content=content,
            mime_type=mime_type,
            prompt=prompt,
            model=self._model,
        )

        model_name = self._model.replace("google/", "")
        url = f"{self._base_url}/v1beta/models/{model_name}:generateContent"
        if self._api_key:
            url += f"?key={self._api_key}"

        data = json.dumps(request.to_dict()).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                return self._parse_response(response_data)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"Google Media Understanding API error: {e.code} - {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Google Media Understanding API connection error: {e.reason}")

    def _parse_response(self, response_data: Dict[str, Any]) -> MediaUnderstandingResult:
        candidates = response_data.get("candidates", [])
        if not candidates:
            return MediaUnderstandingResult(
                description="",
                labels=[],
                objects=[],
                text_content="",
            )

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        text_parts = []
        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])

        full_text = "\n".join(text_parts)
        return MediaUnderstandingResult(
            description=full_text,
            labels=[],
            objects=[],
            text_content=full_text,
        )

    def understand_image(
        self,
        image_data: str,
        prompt: str = "Describe this image in detail.",
    ) -> MediaUnderstandingResult:
        return self.understand(image_data, "image/png", prompt)

    def understand_audio(
        self,
        audio_data: str,
        prompt: str = "Transcribe and describe this audio.",
    ) -> MediaUnderstandingResult:
        return self.understand(audio_data, "audio/wav", prompt)

    def understand_video(
        self,
        video_data: str,
        prompt: str = "Describe this video in detail.",
    ) -> MediaUnderstandingResult:
        return self.understand(video_data, "video/mp4", prompt)