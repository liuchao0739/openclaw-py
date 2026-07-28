import os
import re
from typing import Optional, Dict, Any, List

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import resolve_google_api_key_from_environment
from .model_id import (
    normalize_google_model_id,
    strip_google_provider_prefix,
    infer_google_provider_from_model_id,
)

DEFAULT_GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com"
DEFAULT_VERTEX_BASE_URL = "https://googleapis.com"
DEFAULT_VERTEX_AI_SERVICE_NAME = "aiplatform"
DEFAULT_VERTEX_AI_SERVICE_VERSION = "v1beta1"
DEFAULT_VERTEX_LOCATION = "us-central1"


def resolve_google_base_url(
    provider: Optional[str] = None,
    config: Optional[GoogleConfigDefaults] = None,
) -> str:
    if config:
        if provider == "vertex" and config.google_vertex_ai_http_base_url:
            return config.google_vertex_ai_http_base_url
        if config.google_generative_ai_http_base_url:
            return config.google_generative_ai_http_base_url

    if provider == "vertex":
        vertex_url = os.environ.get("GOOGLE_VERTEX_AI_HTTP_BASE_URL")
        if vertex_url:
            return vertex_url
        return f"{DEFAULT_VERTEX_BASE_URL}/{DEFAULT_VERTEX_AI_SERVICE_NAME}/{DEFAULT_VERTEX_AI_SERVICE_VERSION}/projects/{{project}}/locations/{{location}}"

    base_url = os.environ.get("GOOGLE_GENERATIVE_AI_HTTP_BASE_URL")
    if base_url:
        return base_url
    return DEFAULT_GOOGLE_BASE_URL


def resolve_google_api_endpoint(
    model_id: str,
    config: Optional[GoogleConfigDefaults] = None,
) -> str:
    provider = infer_google_provider_from_model_id(model_id)
    base_url = resolve_google_base_url(provider, config)

    if provider == "vertex/":
        project_id = None
        location = None
        if config:
            project_id = config.google_project_id
            location = config.google_vertex_ai_location
        if not project_id:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        if not location:
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", DEFAULT_VERTEX_LOCATION)
        vertex_path = f"{base_url}/projects/{project_id}/locations/{location}"
        model = strip_google_provider_prefix(model_id)
        return f"{vertex_path}/{DEFAULT_VERTEX_AI_SERVICE_VERSION}/models/{model}"
    else:
        model = strip_google_provider_prefix(model_id)
        return f"{base_url}/v1beta/models/{model}"


def normalize_google_url(
    url: str,
    config: Optional[GoogleConfigDefaults] = None,
) -> str:
    if not url:
        return url
    url = url.rstrip("/")
    return url


def resolve_google_headers(
    api_key: Optional[str] = None,
    auth_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
    }
    if auth_headers:
        headers.update(auth_headers)
    if api_key:
        headers["x-goog-api-key"] = api_key
    return headers


def resolve_google_query_params(
    api_key: Optional[str] = None,
) -> Dict[str, str]:
    params = {}
    if api_key:
        params["key"] = api_key
    return params


def resolve_google_timeout(
    config: Optional[GoogleConfigDefaults] = None,
) -> int:
    if config:
        return config.google_generative_ai_http_request_timeout
    timeout = os.environ.get("GOOGLE_HTTP_REQUEST_TIMEOUT")
    if timeout:
        try:
            return int(timeout)
        except ValueError:
            pass
    return 60000


def resolve_google_request_config(
    model_id: str,
    config: Optional[GoogleConfigDefaults] = None,
) -> Dict[str, Any]:
    api_key = None
    if config:
        api_key = config.google_api_key
    if not api_key:
        api_key = resolve_google_api_key_from_environment()

    return {
        "base_url": resolve_google_base_url(
            infer_google_provider_from_model_id(model_id), config
        ),
        "endpoint": resolve_google_api_endpoint(model_id, config),
        "headers": resolve_google_headers(api_key),
        "params": resolve_google_query_params(api_key),
        "timeout": resolve_google_timeout(config),
        "provider": infer_google_provider_from_model_id(model_id),
    }