from __future__ import annotations

import os
import urllib.request
from typing import Any, Dict, Optional

from .error_utils import format_error_message
from .string_utils import normalize_optional_string


def _resolve_openclaw_attribution_headers() -> Dict[str, str]:
    version = os.environ.get("OPENCLAW_VERSION", "").strip()
    headers = {
        "originator": "openclaw",
    }
    if version:
        headers["version"] = version
        headers["User-Agent"] = f"openclaw/{version}"
    else:
        headers["User-Agent"] = "openclaw"
    return headers


def _is_native_openai_embedding_route(provider: str, base_url: str) -> bool:
    if provider != "openai":
        return False
    try:
        from urllib.parse import urlparse
        hostname = urlparse(base_url).hostname
        if hostname:
            return hostname.lower().rstrip(".") == "api.openai.com"
        return False
    except Exception:
        return False


def resolve_remote_embedding_bearer_client(
    provider: str,
    options: Dict[str, Any],
    default_base_url: str,
) -> Dict[str, Any]:
    remote = (options.get("remote") or {})
    remote_api_key = None
    if remote.get("apiKey"):
        from .secret_input import resolve_memory_secret_input_string
        remote_api_key = resolve_memory_secret_input_string(
            remote.get("apiKey"),
            "agents.*.memorySearch.remote.apiKey",
        )

    remote_base_url = normalize_optional_string(remote.get("baseUrl"))
    provider_config = (((options.get("config") or {}).get("models") or {}).get("providers") or {}).get(provider, {})

    if remote_api_key:
        api_key = remote_api_key
    else:
        api_key = _resolve_api_key_for_provider(provider, options)

    base_url = remote_base_url or normalize_optional_string((provider_config or {}).get("baseUrl")) or default_base_url
    header_overrides = {}
    if provider_config and provider_config.get("headers"):
        header_overrides.update(provider_config["headers"])
    if remote.get("headers"):
        header_overrides.update(remote["headers"])

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    headers.update(header_overrides)

    if _is_native_openai_embedding_route(provider, base_url):
        headers.update(_resolve_openclaw_attribution_headers())

    return {
        "baseUrl": base_url,
        "headers": headers,
        "ssrfPolicy": {"allowPrivateNetwork": False},
    }


def _resolve_api_key_for_provider(provider: str, options: Dict[str, Any]) -> str:
    config = options.get("config") or {}
    providers = ((config.get("models") or {}).get("providers") or {})
    provider_cfg = providers.get(provider) or {}
    api_key = provider_cfg.get("apiKey") or os.environ.get(f"{provider.upper()}_API_KEY", "")
    if not api_key:
        raise RuntimeError(f"API key not found for provider: {provider}")
    return api_key
