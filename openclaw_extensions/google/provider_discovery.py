import os
from typing import Optional, Dict, Any, List

from .config_defaults import GoogleConfigDefaults
from .provider_policy import resolve_google_request_config
from .provider_catalog import lookup_google_model_in_catalog, search_google_catalog
from .model_id import (
    normalize_google_model_id,
    strip_google_provider_prefix,
    infer_google_provider_from_model_id,
    GOOGLE_MODEL_ID_ALIASES,
)


class GoogleProviderDiscovery:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config

    def discover_model(self, model_id: str) -> Dict[str, Any]:
        normalized_id = normalize_google_model_id(model_id)
        provider = infer_google_provider_from_model_id(model_id)
        catalog_entry = lookup_google_model_in_catalog(model_id, provider)
        request_config = resolve_google_request_config(model_id, self.config)

        return {
            "model_id": normalized_id,
            "original_model_id": model_id,
            "provider": provider,
            "catalog_entry": catalog_entry,
            "request_config": request_config,
            "is_known_model": catalog_entry is not None,
        }

    def search_models(self, query: str, provider: str = "google") -> List[Dict[str, Any]]:
        return search_google_catalog(query, provider)

    def get_available_providers(self) -> List[str]:
        return ["google", "vertex"]

    def is_model_supported(
        self,
        model_id: str,
        capability: str,
    ) -> bool:
        provider = infer_google_provider_from_model_id(model_id)
        catalog_entry = lookup_google_model_in_catalog(model_id, provider)
        if not catalog_entry:
            return True
        supports = catalog_entry.get("supports", {})
        return bool(supports.get(capability, False))

    def get_model_capabilities(self, model_id: str) -> Dict[str, Any]:
        provider = infer_google_provider_from_model_id(model_id)
        catalog_entry = lookup_google_model_in_catalog(model_id, provider)
        if catalog_entry:
            return catalog_entry.get("supports", {})
        return {}


def create_google_provider_discovery(config: Optional[GoogleConfigDefaults] = None) -> GoogleProviderDiscovery:
    return GoogleProviderDiscovery(config=config)