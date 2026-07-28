import os
import json
import base64
import mimetypes
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import resolve_google_api_key_from_environment


@dataclass
class ImageGenerationRequest:
    prompt: str
    model: str = "google/imagen-3.0-generate-001"
    number_of_images: int = 1
    size: Optional[str] = None
    aspect_ratio: Optional[str] = None
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None
    output_mime_type: str = "image/png"
    watermark: bool = False
    include_safety_rai: bool = True

    def to_dict(self) -> Dict[str, Any]:
        request: Dict[str, Any] = {
            "prompt": self.prompt,
        }

        generation_config: Dict[str, Any] = {
            "numberOfImages": self.number_of_images,
            "includeSafetyRai": self.include_safety_rai,
            "outputMimeType": self.output_mime_type,
        }

        if self.size:
            generation_config["size"] = self.size
        if self.aspect_ratio:
            generation_config["aspectRatio"] = self.aspect_ratio
        if self.seed is not None:
            generation_config["seed"] = self.seed
        if self.watermark:
            generation_config["watermark"] = self.watermark

        request["generationConfig"] = generation_config
        return request


@dataclass
class GeneratedImage:
    url: Optional[str] = None
    base64_data: Optional[str] = None
    mime_type: str = "image/png"
    width: Optional[int] = None
    height: Optional[int] = None
    seed: Optional[int] = None
    safety_ratings: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "base64_data": self.base64_data,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "safety_ratings": self.safety_ratings,
        }


class GoogleImageGenerationProvider:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._api_key: Optional[str] = None
        self._base_url: str = "https://generativelanguage.googleapis.com"
        self._model: str = "google/imagen-3.0-generate-001"
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
        number_of_images: int = 1,
        size: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        **kwargs: Any,
    ) -> List[GeneratedImage]:
        import urllib.request
        import urllib.error

        self.initialize()

        request = ImageGenerationRequest(
            prompt=prompt,
            model=self._model,
            number_of_images=number_of_images,
            size=size,
            aspect_ratio=aspect_ratio,
            **kwargs,
        )

        model_name = self._model.replace("google/", "")
        url = f"{self._base_url}/v1beta/models/{model_name}:generateImages"
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
            raise RuntimeError(f"Google Image Generation API error: {e.code} - {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Google Image Generation API connection error: {e.reason}")

    def _parse_response(self, response_data: Dict[str, Any]) -> List[GeneratedImage]:
        images = []
        candidates = response_data.get("generatedImages", [])
        if not candidates:
            candidates = response_data.get("candidates", [])
        if not candidates:
            candidates = [response_data]

        for candidate in candidates:
            image_data = candidate.get("image", {})
            generated = GeneratedImage()
            generated.url = image_data.get("url")
            generated.base64_data = image_data.get("base64Data")
            generated.mime_type = image_data.get("mimeType", "image/png")
            generated.width = image_data.get("width")
            generated.height = image_data.get("height")
            generated.seed = candidate.get("seed")
            generated.safety_ratings = candidate.get("safetyRatings", [])
            images.append(generated)
        return images

    def get_supported_sizes(self) -> List[str]:
        return ["256x256", "512x512", "1024x1024", "2048x2048"]

    def get_supported_aspect_ratios(self) -> List[str]:
        return ["1:1", "4:3", "3:4", "16:9", "9:16"]


def create_lazy_google_image_generation_provider(config: Optional[GoogleConfigDefaults] = None) -> GoogleImageGenerationProvider:
    return GoogleImageGenerationProvider(config=config)