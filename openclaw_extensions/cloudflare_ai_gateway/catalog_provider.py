"""Build runtime model catalog entries from stored Cloudflare AI Gateway auth profiles."""

from __future__ import annotations

from typing import Any

from openclaw.config.secrets import coerce_secret_ref
from openclaw.packages.normalization_core import is_record, normalize_optional_string
from openclaw.plugin_sdk.provider_catalog_shared import ModelProviderConfig
from openclaw_extensions.cloudflare_ai_gateway.models import (
    build_cloudflare_ai_gateway_model_definition,
    resolve_cloudflare_ai_gateway_base_url,
)

_NON_ENV_SECRETREF_MARKER = "secretref-managed"


def _resolve_non_env_secret_ref_api_key_marker(_source: str) -> str:
    return _NON_ENV_SECRETREF_MARKER


def _resolve_cloudflare_ai_gateway_api_key(credential: dict[str, Any] | None) -> str | None:
    if not credential or credential.get("type") != "api_key":
        return None

    key_ref = coerce_secret_ref(credential.get("keyRef"))
    key_ref_id = normalize_optional_string(key_ref.get("id") if key_ref else None)
    if key_ref and key_ref_id:
        return (
            key_ref_id
            if key_ref.get("source") == "env"
            else _resolve_non_env_secret_ref_api_key_marker(str(key_ref.get("source", "")))
        )
    return normalize_optional_string(credential.get("key"))


def _resolve_cloudflare_ai_gateway_metadata(
    credential: dict[str, Any] | None,
) -> dict[str, str | None]:
    if not credential or credential.get("type") != "api_key":
        return {}
    metadata = credential.get("metadata")
    if not is_record(metadata):
        return {}
    return {
        "accountId": normalize_optional_string(metadata.get("accountId")),
        "gatewayId": normalize_optional_string(metadata.get("gatewayId")),
    }


def build_cloudflare_ai_gateway_catalog_provider(
    params: dict[str, Any],
) -> ModelProviderConfig | None:
    credential = params.get("credential")
    env_api_key = normalize_optional_string(params.get("envApiKey"))
    api_key = env_api_key or _resolve_cloudflare_ai_gateway_api_key(
        credential if is_record(credential) else None
    )
    if not api_key:
        return None

    metadata = _resolve_cloudflare_ai_gateway_metadata(
        credential if is_record(credential) else None
    )
    account_id = metadata.get("accountId")
    gateway_id = metadata.get("gatewayId")
    if not account_id or not gateway_id:
        return None

    base_url = resolve_cloudflare_ai_gateway_base_url(
        {"accountId": account_id, "gatewayId": gateway_id}
    )
    if not base_url:
        return None

    return {
        "baseUrl": base_url,
        "api": "anthropic-messages",
        "apiKey": api_key,
        "models": [build_cloudflare_ai_gateway_model_definition()],
    }
