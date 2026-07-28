from typing import Optional, Dict, Any, List

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import parse_gemini_auth
from .provider_discovery import GoogleProviderDiscovery


class GoogleDoctorContractAPI:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._discovery = GoogleProviderDiscovery(config=config)

    def check_provider_health(self) -> Dict[str, Any]:
        auth = parse_gemini_auth(self.config)
        return {
            "provider": "google",
            "healthy": auth.get("auth_type") != "none",
            "auth_type": auth.get("auth_type"),
            "has_api_key": bool(auth.get("api_key")),
            "has_project_id": bool(auth.get("project_id")),
            "message": "Provider is ready" if auth.get("auth_type") != "none" else "Provider is not configured",
        }

    def check_model_health(self, model_id: str) -> Dict[str, Any]:
        try:
            discovery = self._discovery.discover_model(model_id)
            return {
                "model_id": model_id,
                "healthy": True,
                "provider": discovery.get("provider"),
                "is_known_model": discovery.get("is_known_model"),
                "message": "Model is available",
            }
        except Exception as e:
            return {
                "model_id": model_id,
                "healthy": False,
                "message": str(e),
            }

    def get_contract(self) -> Dict[str, Any]:
        return {
            "provider": "google",
            "version": "1.0.0",
            "min_protocol_version": "1.0.0",
            "supported_model_types": [
                "text",
                "image",
                "video",
                "audio",
                "embedding",
                "speech",
                "realtime_voice",
                "web_search",
            ],
            "capabilities": {
                "streaming": True,
                "batch_processing": True,
                "thinking": True,
                "reasoning": True,
                "tool_use": True,
                "structured_output": True,
            },
        }