from typing import Optional, Dict, Any, List

from .config_defaults import GoogleConfigDefaults
from .provider_policy import (
    resolve_google_base_url,
    resolve_google_api_endpoint,
    resolve_google_request_config,
    resolve_google_headers,
    resolve_google_query_params,
)
from .model_id import (
    normalize_google_model_id,
    infer_google_provider_from_model_id,
)


class GoogleProviderPolicyAPI:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config

    def resolve_policy(self, model_id: str) -> Dict[str, Any]:
        return resolve_google_request_config(model_id, self.config)

    def resolve_endpoint_policy(self, model_id: str) -> Dict[str, Any]:
        provider = infer_google_provider_from_model_id(model_id)
        return {
            "base_url": resolve_google_base_url(provider, self.config),
            "endpoint": resolve_google_api_endpoint(model_id, self.config),
            "provider": provider,
        }

    def get_policy_definition(self) -> Dict[str, Any]:
        return {
            "policy_type": "url_resolution",
            "rules": [
                "Normalize model IDs to canonical format",
                "Route to correct provider based on model ID prefix",
                "Resolve base URL based on provider type",
                "Apply authentication headers and query parameters",
                "Configure timeouts based on request type",
            ],
            "supported_providers": ["google", "vertex"],
        }

    def validate_policy(self, model_id: str) -> Dict[str, Any]:
        provider = infer_google_provider_from_model_id(model_id)
        valid_providers = ["google/", "vertex/"]
        is_valid = provider in valid_providers
        return {
            "valid": is_valid,
            "model_id": model_id,
            "provider": provider,
            "normalized_id": normalize_google_model_id(model_id),
            "message": "Policy is valid" if is_valid else f"Unknown provider: {provider}",
        }

    def get_request_policy(self, model_id: str) -> Dict[str, Any]:
        config = resolve_google_request_config(model_id, self.config)
        return {
            "headers": config.get("headers", {}),
            "params": config.get("params", {}),
            "timeout": config.get("timeout", 60000),
            "base_url": config.get("base_url", ""),
            "endpoint": config.get("endpoint", ""),
        }