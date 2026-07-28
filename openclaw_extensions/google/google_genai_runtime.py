import os
import json
from typing import Optional, Dict, Any, List

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import resolve_google_api_key_from_environment, parse_gemini_auth
from .provider_policy import (
    resolve_google_base_url,
    resolve_google_api_endpoint,
    resolve_google_headers,
    resolve_google_query_params,
    resolve_google_timeout,
)
from .model_id import infer_google_provider_from_model_id


class GoogleGenAIRuntime:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._api_key: Optional[str] = None
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        auth = parse_gemini_auth(self.config)
        self._api_key = auth.get("api_key")
        self._initialized = True

    def get_endpoint(self, model_id: str) -> str:
        return resolve_google_api_endpoint(model_id, self.config)

    def get_base_url(self, model_id: str) -> str:
        provider = infer_google_provider_from_model_id(model_id)
        return resolve_google_base_url(provider, self.config)

    def get_headers(self, model_id: str) -> Dict[str, str]:
        self.initialize()
        return resolve_google_headers(self._api_key)

    def get_params(self, model_id: str) -> Dict[str, str]:
        self.initialize()
        return resolve_google_query_params(self._api_key)

    def get_timeout(self) -> int:
        return resolve_google_timeout(self.config)

    def build_request_url(self, model_id: str, action: str = "generateContent") -> str:
        endpoint = self.get_endpoint(model_id)
        url = f"{endpoint}:{action}"
        params = self.get_params(model_id)
        if params:
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query_string}"
        return url

    def build_request(
        self,
        model_id: str,
        request_body: Dict[str, Any],
        action: str = "generateContent",
    ) -> Dict[str, Any]:
        return {
            "url": self.build_request_url(model_id, action),
            "method": "POST",
            "headers": self.get_headers(model_id),
            "body": request_body,
            "timeout": self.get_timeout(),
        }

    def get_runtime_info(self) -> Dict[str, Any]:
        self.initialize()
        return {
            "provider": "google",
            "runtime": "genai",
            "version": "1.0.0",
            "has_api_key": bool(self._api_key),
            "default_base_url": resolve_google_base_url("google", self.config),
            "vertex_base_url": resolve_google_base_url("vertex", self.config),
        }

    def is_available(self) -> bool:
        self.initialize()
        return bool(self._api_key)

    def get_supported_actions(self) -> List[str]:
        return [
            "generateContent",
            "streamGenerateContent",
            "embedText",
            "batchEmbedContents",
            "generateImages",
            "generateVideos",
            "generateAudio",
            "predict",
        ]


def create_google_genai_runtime(config: Optional[GoogleConfigDefaults] = None) -> GoogleGenAIRuntime:
    return GoogleGenAIRuntime(config=config)