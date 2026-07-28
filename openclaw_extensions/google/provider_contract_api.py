from typing import Optional, Dict, Any, List

from .config_defaults import GoogleConfigDefaults
from .provider_discovery import GoogleProviderDiscovery
from .provider_catalog import build_google_static_catalog_provider


class GoogleProviderContractAPI:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._discovery = GoogleProviderDiscovery(config=config)

    def get_provider_contract(self) -> Dict[str, Any]:
        return {
            "provider_id": "google",
            "provider_name": "Google",
            "version": "1.0.0",
            "supported_providers": [
                {
                    "id": "google",
                    "name": "Google Generative AI",
                    "base_url": "https://generativelanguage.googleapis.com",
                },
                {
                    "id": "vertex",
                    "name": "Google Cloud Vertex AI",
                    "base_url": "https://googleapis.com",
                },
            ],
            "model_catalog": build_google_static_catalog_provider("google"),
        }

    def get_model_contract(self, model_id: str) -> Optional[Dict[str, Any]]:
        discovery = self._discovery.discover_model(model_id)
        return discovery

    def list_model_contracts(self, provider: str = "google") -> List[Dict[str, Any]]:
        catalog = build_google_static_catalog_provider(provider)
        return catalog.get("models", [])

    def validate_provider_contract(self) -> Dict[str, Any]:
        contract = self.get_provider_contract()
        return {
            "valid": True,
            "provider_id": contract.get("provider_id"),
            "supported_providers": len(contract.get("supported_providers", [])),
            "message": "Provider contract is valid",
        }