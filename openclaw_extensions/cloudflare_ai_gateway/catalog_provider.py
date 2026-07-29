from typing import Any, Optional

from .._sdk import normalize_secret_input
from .models import (
    build_cloudflare_ai_gateway_model_definition,
    resolve_cloudflare_ai_gateway_base_url,
)


def _trim_to_undefined(value: Any) -> Optional[str]:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return None


def _resolve_cloudflare_ai_gateway_api_key(cred: Any) -> Optional[str]:
    if not isinstance(cred, dict) or cred.get("type") != "api_key":
        return None
    key_ref = cred.get("keyRef")
    if isinstance(key_ref, dict):
        key_ref_id = _trim_to_undefined(key_ref.get("id"))
        if key_ref_id:
            source = key_ref.get("source")
            if source == "env":
                return key_ref_id
            return f"ref:{source}:{key_ref_id}"
    return _trim_to_undefined(cred.get("key"))


def _resolve_cloudflare_ai_gateway_metadata(cred: Any) -> dict:
    if not isinstance(cred, dict) or cred.get("type") != "api_key":
        return {}
    metadata = cred.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "accountId": _trim_to_undefined(metadata.get("accountId")),
        "gatewayId": _trim_to_undefined(metadata.get("gatewayId")),
    }


def build_cloudflare_ai_gateway_catalog_provider(params: dict) -> Optional[dict]:
    credential = params.get("credential")
    env_api_key = _trim_to_undefined(params.get("envApiKey"))
    api_key = env_api_key or _resolve_cloudflare_ai_gateway_api_key(credential)
    if not api_key:
        return None
    metadata = _resolve_cloudflare_ai_gateway_metadata(credential)
    account_id = metadata.get("accountId")
    gateway_id = metadata.get("gatewayId")
    if not account_id or not gateway_id:
        return None
    base_url = resolve_cloudflare_ai_gateway_base_url({
        "accountId": account_id,
        "gatewayId": gateway_id,
    })
    if not base_url:
        return None
    return {
        "baseUrl": base_url,
        "api": "anthropic-messages",
        "apiKey": api_key,
        "models": [build_cloudflare_ai_gateway_model_definition()],
    }
