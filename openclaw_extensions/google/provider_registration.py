from typing import Optional, Dict, Any, Callable

from .config_defaults import GoogleConfigDefaults
from .provider_policy import resolve_google_request_config
from .provider_discovery import GoogleProviderDiscovery
from .embedding_provider import GoogleEmbeddingProvider
from .image_generation_provider import GoogleImageGenerationProvider
from .media_understanding_provider import GoogleMediaUnderstandingProvider
from .speech_provider import GoogleSpeechProvider
from .video_generation_provider import GoogleVideoGenerationProvider
from .music_generation_provider import GoogleMusicGenerationProvider
from .realtime_voice_provider import GoogleRealtimeVoiceProvider
from .web_search_provider import GoogleWebSearchProvider
from .memory_embedding_adapter import MemoryEmbeddingAdapter
from .generation_provider_metadata import GenerationProviderMetadata


class GoogleProviderRegistry:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._providers: Dict[str, Any] = {}
        self._registered = False

    def register_all(self) -> None:
        if self._registered:
            return

        self._register_embedding_provider()
        self._register_image_generation_provider()
        self._register_media_understanding_provider()
        self._register_speech_provider()
        self._register_video_generation_provider()
        self._register_music_generation_provider()
        self._register_realtime_voice_provider()
        self._register_web_search_provider()
        self._register_memory_embedding_provider()

        self._registered = True

    def _register_embedding_provider(self) -> None:
        provider = GoogleEmbeddingProvider(config=self.config)
        self._providers["embedding"] = provider

    def _register_image_generation_provider(self) -> None:
        provider = GoogleImageGenerationProvider(config=self.config)
        self._providers["image_generation"] = provider

    def _register_media_understanding_provider(self) -> None:
        provider = GoogleMediaUnderstandingProvider(config=self.config)
        self._providers["media_understanding"] = provider

    def _register_speech_provider(self) -> None:
        provider = GoogleSpeechProvider(config=self.config)
        self._providers["speech"] = provider

    def _register_video_generation_provider(self) -> None:
        provider = GoogleVideoGenerationProvider(config=self.config)
        self._providers["video_generation"] = provider

    def _register_music_generation_provider(self) -> None:
        provider = GoogleMusicGenerationProvider(config=self.config)
        self._providers["music_generation"] = provider

    def _register_realtime_voice_provider(self) -> None:
        provider = GoogleRealtimeVoiceProvider(config=self.config)
        self._providers["realtime_voice"] = provider

    def _register_web_search_provider(self) -> None:
        provider = GoogleWebSearchProvider(config=self.config)
        self._providers["web_search"] = provider

    def _register_memory_embedding_provider(self) -> None:
        adapter = MemoryEmbeddingAdapter(config=self.config)
        self._providers["memory_embedding"] = adapter

    def get_provider(self, provider_type: str) -> Optional[Any]:
        return self._providers.get(provider_type)

    def get_metadata(self) -> GenerationProviderMetadata:
        return GenerationProviderMetadata()

    def list_providers(self) -> list:
        return list(self._providers.keys())

    def is_registered(self) -> bool:
        return self._registered


def register_google_plugin(config: Optional[GoogleConfigDefaults] = None) -> GoogleProviderRegistry:
    registry = GoogleProviderRegistry(config=config)
    registry.register_all()
    return registry