"""Anthropic Vertex region, project, and ADC auth detection helpers."""

from __future__ import annotations

import os
import platform
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from openclaw.packages.normalization_core import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
)

ANTHROPIC_VERTEX_DEFAULT_REGION = "global"
ANTHROPIC_VERTEX_REGION_RE = re.compile(r"^[a-z0-9-]+$")
GCP_VERTEX_CREDENTIALS_MARKER = "gcp-vertex-credentials"

_GOOGLE_VERTEX_HOSTS = {
    "aiplatform.googleapis.com": "global",
    "aiplatform.eu.rep.googleapis.com": "eu",
    "aiplatform.us.rep.googleapis.com": "us",
}
_GOOGLE_VERTEX_HOST_SUFFIX = "-aiplatform.googleapis.com"


def _normalize_optional_secret_input(value: Any) -> str | None:
    return normalize_optional_string(value)


def _resolve_url_hostname(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    trimmed = value.strip()
    try:
        return urlparse(trimmed).hostname
    except ValueError:
        return None


def resolve_provider_endpoint(base_url: str | None) -> dict[str, Any]:
    """Resolve provider endpoint metadata for a base URL."""
    if not isinstance(base_url, str) or not base_url.strip():
        return {"endpointClass": "default"}
    host = _resolve_url_hostname(base_url)
    if not host:
        return {"endpointClass": "invalid"}

    if host in _GOOGLE_VERTEX_HOSTS:
        return {
            "endpointClass": "google-vertex",
            "hostname": host,
            "googleVertexRegion": _GOOGLE_VERTEX_HOSTS[host],
        }
    if host.endswith(_GOOGLE_VERTEX_HOST_SUFFIX):
        return {
            "endpointClass": "google-vertex",
            "hostname": host,
            "googleVertexRegion": host[: -len(_GOOGLE_VERTEX_HOST_SUFFIX)],
        }
    return {"endpointClass": "custom", "hostname": host}


def resolve_anthropic_vertex_region(env: Mapping[str, str] | None = None) -> str:
    """Resolve the configured Vertex region, defaulting to global."""
    resolved_env = env if env is not None else os.environ
    region = (
        _normalize_optional_secret_input(resolved_env.get("GOOGLE_CLOUD_LOCATION"))
        or _normalize_optional_secret_input(resolved_env.get("CLOUD_ML_REGION"))
    )
    if region and ANTHROPIC_VERTEX_REGION_RE.fullmatch(region):
        return region
    return ANTHROPIC_VERTEX_DEFAULT_REGION


def resolve_anthropic_vertex_project_id_from_adc(env: Mapping[str, str] | None = None) -> str | None:
    resolved_env = env if env is not None else os.environ
    credentials_path = resolve_anthropic_vertex_adc_credentials_path_candidate(resolved_env)
    if not credentials_path:
        return None
    try:
        import json

        parsed = json.loads(Path(credentials_path).read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            return None
        return (
            _normalize_optional_secret_input(parsed.get("project_id"))
            or _normalize_optional_secret_input(parsed.get("quota_project_id"))
        )
    except (OSError, ValueError, TypeError):
        return None


def resolve_anthropic_vertex_project_id(env: Mapping[str, str] | None = None) -> str | None:
    """Resolve the Vertex project id from explicit env or ADC files."""
    resolved_env = env if env is not None else os.environ
    return (
        _normalize_optional_secret_input(resolved_env.get("ANTHROPIC_VERTEX_PROJECT_ID"))
        or _normalize_optional_secret_input(resolved_env.get("GOOGLE_CLOUD_PROJECT"))
        or _normalize_optional_secret_input(resolved_env.get("GOOGLE_CLOUD_PROJECT_ID"))
        or resolve_anthropic_vertex_project_id_from_adc(resolved_env)
    )


def resolve_anthropic_vertex_region_from_base_url(base_url: str | None = None) -> str | None:
    """Extract a Vertex region from a provider base URL when possible."""
    endpoint = resolve_provider_endpoint(base_url)
    if endpoint.get("endpointClass") != "google-vertex":
        return None
    region = endpoint.get("googleVertexRegion")
    return region if isinstance(region, str) else None


def resolve_anthropic_vertex_client_region(
    params: dict[str, Any] | None = None,
) -> str:
    """Resolve the client region from model base URL first, then env fallback."""
    base_url = params.get("baseUrl") if params else None
    if base_url is None and params:
        base_url = params.get("base_url")
    env = params.get("env") if params else None
    return (
        resolve_anthropic_vertex_region_from_base_url(base_url)
        or resolve_anthropic_vertex_region(env)
    )


def _has_anthropic_vertex_metadata_server_adc(env: Mapping[str, str]) -> bool:
    explicit_metadata_opt_in = _normalize_optional_secret_input(
        env.get("ANTHROPIC_VERTEX_USE_GCP_METADATA")
    )
    return (
        explicit_metadata_opt_in == "1"
        or normalize_lowercase_string_or_empty(explicit_metadata_opt_in) == "true"
    )


def resolve_anthropic_vertex_home_dir(env: Mapping[str, str]) -> str:
    return (
        _normalize_optional_secret_input(env.get("HOME"))
        or _normalize_optional_secret_input(env.get("USERPROFILE"))
        or str(Path.home())
    )


def resolve_anthropic_vertex_default_adc_path(env: Mapping[str, str]) -> str:
    if platform.system() == "Windows":
        app_data = _normalize_optional_secret_input(env.get("APPDATA"))
        base = app_data or str(
            Path(resolve_anthropic_vertex_home_dir(env)) / "AppData" / "Roaming"
        )
        return str(Path(base) / "gcloud" / "application_default_credentials.json")
    return str(
        Path(resolve_anthropic_vertex_home_dir(env))
        / ".config"
        / "gcloud"
        / "application_default_credentials.json"
    )


def resolve_anthropic_vertex_adc_credentials_path_candidate(
    env: Mapping[str, str] | None = None,
) -> str | None:
    resolved_env = env if env is not None else os.environ
    explicit = _normalize_optional_secret_input(resolved_env.get("GOOGLE_APPLICATION_CREDENTIALS"))
    if explicit:
        return explicit
    return resolve_anthropic_vertex_default_adc_path(resolved_env)


def can_read_anthropic_vertex_adc(env: Mapping[str, str] | None = None) -> bool:
    credentials_path = resolve_anthropic_vertex_adc_credentials_path_candidate(env)
    if not credentials_path:
        return False
    try:
        Path(credentials_path).read_text(encoding="utf-8")
        return True
    except OSError:
        return False


def has_anthropic_vertex_credentials(env: Mapping[str, str] | None = None) -> bool:
    """Return whether ADC credentials or metadata-server auth are available."""
    resolved_env = env if env is not None else os.environ
    return _has_anthropic_vertex_metadata_server_adc(resolved_env) or can_read_anthropic_vertex_adc(
        resolved_env
    )


def has_anthropic_vertex_available_auth(env: Mapping[str, str] | None = None) -> bool:
    """Return whether Anthropic Vertex has usable auth for implicit registration."""
    return has_anthropic_vertex_credentials(env)


def resolve_anthropic_vertex_config_api_key(env: Mapping[str, str] | None = None) -> str | None:
    """Resolve the synthetic config API key marker for Anthropic Vertex auth."""
    return GCP_VERTEX_CREDENTIALS_MARKER if has_anthropic_vertex_available_auth(env) else None
