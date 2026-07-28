from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class GenerationProviderMetadata:
    provider_id: str = "google"
    provider_name: str = "Google"
    provider_version: str = "1.0.0"
    supports_image_generation: bool = True
    supports_video_generation: bool = True
    supports_music_generation: bool = True
    supports_speech_generation: bool = True
    supports_media_understanding: bool = True
    supports_embedding: bool = True
    supports_realtime_voice: bool = True
    supports_web_search: bool = True
    supports_text_generation: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "supports_image_generation": self.supports_image_generation,
            "supports_video_generation": self.supports_video_generation,
            "supports_music_generation": self.supports_music_generation,
            "supports_speech_generation": self.supports_speech_generation,
            "supports_media_understanding": self.supports_media_understanding,
            "supports_embedding": self.supports_embedding,
            "supports_realtime_voice": self.supports_realtime_voice,
            "supports_web_search": self.supports_web_search,
            "supports_text_generation": self.supports_text_generation,
        }