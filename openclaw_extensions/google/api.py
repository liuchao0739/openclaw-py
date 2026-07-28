from typing import Optional, Dict, Any

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import (
    parse_gemini_auth as _parse_gemini_auth,
    resolve_google_api_key_from_environment as _resolve_google_api_key_from_environment,
    infer_google_project_id as _infer_google_project_id,
    resolve_google_project_id_from_environment as _resolve_google_project_id_from_environment,
    resolve_google_project_id_from_gcloud_config as _resolve_google_project_id_from_gcloud_config,
    resolve_google_project_id_from_application_default_credentials as _resolve_google_project_id_from_application_default_credentials,
    resolve_google_location_from_environment as _resolve_google_location_from_environment,
    resolve_google_generative_ai_http_request_config as _resolve_google_generative_ai_http_request_config,
)
from .model_id import (
    normalize_google_model_id as _normalize_google_model_id,
    strip_google_provider_prefix as _strip_google_provider_prefix,
    parse_google_model_id as _parse_google_model_id,
    is_google_model_id as _is_google_model_id,
    infer_google_provider_from_model_id as _infer_google_provider_from_model_id,
)
from .provider_policy import (
    resolve_google_base_url as _resolve_google_base_url,
    resolve_google_api_endpoint as _resolve_google_api_endpoint,
    resolve_google_request_config as _resolve_google_request_config,
)


def parse_gemini_auth(config: Optional[GoogleConfigDefaults] = None) -> Dict[str, Any]:
    return _parse_gemini_auth(config)


def normalize_google_model_id(model_id: str, provider: Optional[str] = None) -> str:
    return _normalize_google_model_id(model_id, provider)


def resolve_google_generative_ai_http_request_config(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: Optional[int] = None,
    config: Optional[GoogleConfigDefaults] = None,
) -> Dict[str, Any]:
    return _resolve_google_generative_ai_http_request_config(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        config=config,
    )


def resolve_google_api_key_from_environment() -> Optional[str]:
    return _resolve_google_api_key_from_environment()


def infer_google_project_id() -> Optional[str]:
    return _infer_google_project_id()


def resolve_google_project_id_from_environment() -> Optional[str]:
    return _resolve_google_project_id_from_environment()


def resolve_google_project_id_from_gcloud_config() -> Optional[str]:
    return _resolve_google_project_id_from_gcloud_config()


def resolve_google_project_id_from_application_default_credentials() -> Optional[str]:
    return _resolve_google_project_id_from_application_default_credentials()


def resolve_google_location_from_environment() -> Optional[str]:
    return _resolve_google_location_from_environment()


def strip_google_provider_prefix(model_id: str) -> str:
    return _strip_google_provider_prefix(model_id)


def is_google_model_id(model_id: str) -> bool:
    return _is_google_model_id(model_id)


def resolve_google_api_endpoint(
    model_id: str,
    config: Optional[GoogleConfigDefaults] = None,
) -> str:
    return _resolve_google_api_endpoint(model_id, config)


def resolve_google_request_config(
    model_id: str,
    config: Optional[GoogleConfigDefaults] = None,
) -> Dict[str, Any]:
    return _resolve_google_request_config(model_id, config)