import os
import re
from pathlib import Path
from typing import Any, Mapping, Optional

ANTHROPIC_VERTEX_DEFAULT_REGION = "global"
ANTHROPIC_VERTEX_REGION_RE = re.compile(r"^[a-z0-9-]+$")
GCP_VERTEX_CREDENTIALS_MARKER = "gcp-vertex-credentials"


def _normalize_optional_secret_input(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _normalize_lowercase_string_or_empty(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def resolve_anthropic_vertex_region(env: Optional[Mapping[str, str]] = None) -> str:
    env_map = env if env is not None else os.environ
    region = _normalize_optional_secret_input(env_map.get("GOOGLE_CLOUD_LOCATION")) or _normalize_optional_secret_input(env_map.get("CLOUD_ML_REGION"))
    if region and ANTHROPIC_VERTEX_REGION_RE.match(region):
        return region
    return ANTHROPIC_VERTEX_DEFAULT_REGION


def resolve_anthropic_vertex_project_id(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    env_map = env if env is not None else os.environ
    return (
        _normalize_optional_secret_input(env_map.get("ANTHROPIC_VERTEX_PROJECT_ID"))
        or _normalize_optional_secret_input(env_map.get("GOOGLE_CLOUD_PROJECT"))
        or _normalize_optional_secret_input(env_map.get("GOOGLE_CLOUD_PROJECT_ID"))
        or _resolve_anthropic_vertex_project_id_from_adc(env_map)
    )


def resolve_anthropic_vertex_region_from_base_url(base_url: Optional[str]) -> Optional[str]:
    from openclaw.plugin_sdk.provider_http import resolve_provider_endpoint

    endpoint = resolve_provider_endpoint(base_url)
    if endpoint.get("endpointClass") == "google-vertex":
        return endpoint.get("googleVertexRegion")
    return None


def resolve_anthropic_vertex_client_region(params: Optional[dict] = None) -> str:
    params = params or {}
    return (
        resolve_anthropic_vertex_region_from_base_url(params.get("baseUrl"))
        or resolve_anthropic_vertex_region(params.get("env"))
    )


def _has_anthropic_vertex_metadata_server_adc(env: Mapping[str, str]) -> bool:
    explicit_metadata_opt_in = _normalize_optional_secret_input(env.get("ANTHROPIC_VERTEX_USE_GCP_METADATA"))
    return explicit_metadata_opt_in == "1" or _normalize_lowercase_string_or_empty(explicit_metadata_opt_in) == "true"


def _resolve_anthropic_vertex_home_dir(env: Mapping[str, str]) -> str:
    return (
        _normalize_optional_secret_input(env.get("HOME"))
        or _normalize_optional_secret_input(env.get("USERPROFILE"))
        or str(Path.home())
    )


def _resolve_anthropic_vertex_default_adc_path(env: Mapping[str, str]) -> str:
    import platform

    if platform.system() == "Windows":
        appdata = _normalize_optional_secret_input(env.get("APPDATA")) or str(Path(_resolve_anthropic_vertex_home_dir(env), "AppData", "Roaming"))
        return str(Path(appdata, "gcloud", "application_default_credentials.json"))
    return str(Path(_resolve_anthropic_vertex_home_dir(env), ".config", "gcloud", "application_default_credentials.json"))


def _resolve_anthropic_vertex_adc_credentials_path_candidate(env: Mapping[str, str]) -> Optional[str]:
    explicit = _normalize_optional_secret_input(env.get("GOOGLE_APPLICATION_CREDENTIALS"))
    if explicit:
        return explicit
    return _resolve_anthropic_vertex_default_adc_path(env)


def _can_read_anthropic_vertex_adc(env: Mapping[str, str]) -> bool:
    credentials_path = _resolve_anthropic_vertex_adc_credentials_path_candidate(env)
    if not credentials_path:
        return False
    try:
        Path(credentials_path).read_text(encoding="utf-8")
        return True
    except OSError:
        return False


def _resolve_anthropic_vertex_project_id_from_adc(env: Mapping[str, str]) -> Optional[str]:
    credentials_path = _resolve_anthropic_vertex_adc_credentials_path_candidate(env)
    if not credentials_path:
        return None
    try:
        import json

        parsed = json.loads(Path(credentials_path).read_text(encoding="utf-8"))
        return (
            _normalize_optional_secret_input(parsed.get("project_id"))
            or _normalize_optional_secret_input(parsed.get("quota_project_id"))
        )
    except (OSError, ValueError):
        return None


def has_anthropic_vertex_credentials(env: Optional[Mapping[str, str]] = None) -> bool:
    env_map = env if env is not None else os.environ
    return _has_anthropic_vertex_metadata_server_adc(env_map) or _can_read_anthropic_vertex_adc(env_map)


def has_anthropic_vertex_available_auth(env: Optional[Mapping[str, str]] = None) -> bool:
    return has_anthropic_vertex_credentials(env)


def resolve_anthropic_vertex_config_api_key(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    if has_anthropic_vertex_available_auth(env):
        return GCP_VERTEX_CREDENTIALS_MARKER
    return None
