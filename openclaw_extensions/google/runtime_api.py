from typing import Optional, Dict, Any, List

from .config_defaults import GoogleConfigDefaults
from .provider_discovery import GoogleProviderDiscovery
from .provider_catalog import build_google_static_catalog_provider


class GoogleRuntimeAPI:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._discovery = GoogleProviderDiscovery(config=config)

    def get_runtime_info(self) -> Dict[str, Any]:
        return {
            "provider": "google",
            "version": "1.0.0",
            "supported_providers": ["google", "vertex"],
            "discovery": self._discovery.get_available_providers(),
        }

    def discover_model(self, model_id: str) -> Dict[str, Any]:
        return self._discovery.discover_model(model_id)

    def search_models(self, query: str, provider: str = "google") -> List[Dict[str, Any]]:
        return self._discovery.search_models(query, provider)

    def get_catalog(self, provider: str = "google") -> Dict[str, Any]:
        return build_google_static_catalog_provider(provider)

    def is_model_supported(self, model_id: str, capability: str) -> bool:
        return self._discovery.is_model_supported(model_id, capability)

    def get_model_capabilities(self, model_id: str) -> Dict[str, Any]:
        return self._discovery.get_model_capabilities(model_id)