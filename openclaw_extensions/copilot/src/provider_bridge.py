# Copilot plugin module implements BYOK provider mapping.
# ruff: noqa: BLE001

from __future__ import annotations

import ipaddress
import json
import unicodedata
from typing import Any, Literal, NotRequired, TypedDict
from urllib.parse import parse_qsl, urlparse, urlunparse

from openclaw_extensions.copilot.src.auth_bridge import token_fingerprint

COPILOT_BYOK_PROVIDER_ERROR = (
    "[copilot-attempt] BYOK requires an OpenAI-compatible or Anthropic model api "
    "and a non-empty baseUrl"
)
COPILOT_BYOK_TRANSPORT_POLICY_ERROR = (
    "[copilot-attempt] BYOK does not support OpenClaw provider request proxy, TLS, "
    "or private-network policy overrides"
)
COPILOT_BYOK_ENDPOINT_POLICY_ERROR = (
    "[copilot-attempt] BYOK endpoint is blocked by OpenClaw SSRF policy"
)

_CREDENTIAL_QUERY_PARAM_NAMES = frozenset(
    {
        "accesstoken",
        "appsecret",
        "auth",
        "authtoken",
        "apikey",
        "authorization",
        "clientsecret",
        "code",
        "credential",
        "hooktoken",
        "idtoken",
        "jwt",
        "key",
        "pass",
        "passwd",
        "password",
        "privatekey",
        "refreshtoken",
        "secret",
        "session",
        "sig",
        "signature",
        "token",
        "xapikey",
        "xaccesstoken",
        "xamzsecuritytoken",
        "xamzsignature",
        "xauthtoken",
    }
)

_OAUTH_API_KEY_MARKER_PREFIX = "oauth:"
_OLLAMA_LOCAL_AUTH_MARKER = "ollama-local"
_CUSTOM_LOCAL_AUTH_MARKER = "custom-local"
_CODEX_APP_SERVER_AUTH_MARKER = "codex-app-server"
_GCP_VERTEX_CREDENTIALS_MARKER = "gcp-vertex-credentials"
_NON_ENV_SECRETREF_MARKER = "secretref-managed"
_SECRETREF_ENV_HEADER_MARKER_PREFIX = "secretref-env:"

_AWS_SDK_ENV_MARKERS = frozenset(
    {
        "AWS_BEARER_TOKEN_BEDROCK",
        "AWS_ACCESS_KEY_ID",
        "AWS_PROFILE",
    }
)

_CORE_NON_SECRET_API_KEY_MARKERS = frozenset(
    {
        _CUSTOM_LOCAL_AUTH_MARKER,
        _CODEX_APP_SERVER_AUTH_MARKER,
        _GCP_VERTEX_CREDENTIALS_MARKER,
        _OLLAMA_LOCAL_AUTH_MARKER,
        _NON_ENV_SECRETREF_MARKER,
    }
)

_LEGACY_ENV_API_KEY_MARKERS = frozenset(
    {
        "GOOGLE_API_KEY",
        "DEEPSEEK_API_KEY",
        "PERPLEXITY_API_KEY",
        "FIREWORKS_API_KEY",
        "NOVITA_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "AZURE_API_KEY",
        "MINIMAX_CODE_PLAN_KEY",
    }
)

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
    }
)

CopilotProviderMode = Literal["github-copilot", "byok"]


class CopilotModelProviderInput(TypedDict):
    id: str
    provider: str
    api: NotRequired[str]
    base_url: NotRequired[str]
    azure_api_version: NotRequired[str]
    headers: NotRequired[dict[str, str | None]]
    auth_header: NotRequired[bool]
    request_auth_mode: NotRequired[str]
    request_proxy: NotRequired[Any]
    request_tls: NotRequired[Any]
    request_allow_private_network: NotRequired[Any]
    context_tokens: NotRequired[int]
    context_window: NotRequired[int]
    max_tokens: NotRequired[int]


class ProviderConfig(TypedDict, total=False):
    type: str
    wire_api: str
    base_url: str
    model_id: str
    wire_model: str
    bearer_token: str
    api_key: str
    headers: dict[str, str]
    azure: dict[str, str]
    max_prompt_tokens: int
    max_output_tokens: int


class ResolvedCopilotProvider(TypedDict, total=False):
    mode: CopilotProviderMode
    provider: ProviderConfig
    auth_profile_id: str
    auth_profile_version: str


def resolve_copilot_provider(
    *,
    model: CopilotModelProviderInput,
    resolved_api_key: str | None = None,
    auth_profile_id: str | None = None,
) -> ResolvedCopilotProvider:
    if model["provider"].strip().lower() == "github-copilot":
        return {"mode": "github-copilot"}

    base_url = _read_string(model.get("base_url"))
    if not base_url:
        raise ValueError(COPILOT_BYOK_PROVIDER_ERROR)
    _assert_byok_endpoint_allowed(base_url)
    if _has_unsupported_transport_policy(model):
        raise ValueError(COPILOT_BYOK_TRANSPORT_POLICY_ERROR)

    api = (_read_string(model.get("api")) or "openai-responses").lower()
    provider = _resolve_provider_type(api, base_url, model.get("azure_api_version"))
    resolved_credential = _resolve_provider_credential(resolved_api_key)
    headers = _resolve_provider_headers(model.get("headers"))
    request_auth_mode = _read_string(model.get("request_auth_mode"))
    request_auth_mode_lower = request_auth_mode.lower() if request_auth_mode else None
    use_prepared_request_auth = (
        request_auth_mode_lower is not None and request_auth_mode_lower != "provider-default"
    )

    provider_config: ProviderConfig = {
        "type": provider["type"],
        "base_url": provider["base_url"],
        "model_id": model["id"],
        "wire_model": model["id"],
    }
    if provider.get("wire_api"):
        provider_config["wire_api"] = provider["wire_api"]
    if resolved_credential and not use_prepared_request_auth:
        if model.get("auth_header"):
            provider_config["bearer_token"] = resolved_credential
        else:
            provider_config["api_key"] = resolved_credential
    if headers:
        provider_config["headers"] = headers
    if provider.get("azure"):
        provider_config["azure"] = provider["azure"]
    max_prompt_tokens = model.get("context_tokens") or model.get("context_window")
    if max_prompt_tokens:
        provider_config["max_prompt_tokens"] = max_prompt_tokens
    if model.get("max_tokens"):
        provider_config["max_output_tokens"] = model["max_tokens"]

    trimmed_auth_profile_id = (auth_profile_id or "").strip()
    resolved_auth_profile_id = trimmed_auth_profile_id or f"byok:{model['provider']}"
    auth_profile_version = token_fingerprint(
        _stable_serialize(
            {
                "api": api,
                "baseUrl": provider["base_url"],
                "azureApiVersion": provider.get("azure", {}).get("apiVersion"),
                "headers": headers,
                "authHeader": model.get("auth_header"),
                "requestAuthMode": model.get("request_auth_mode"),
                "apiKey": resolved_credential,
                "modelId": model["id"],
                "maxPromptTokens": max_prompt_tokens,
                "maxOutputTokens": model.get("max_tokens"),
            }
        )
    )

    return {
        "mode": "byok",
        "provider": provider_config,
        "auth_profile_id": resolved_auth_profile_id,
        "auth_profile_version": auth_profile_version,
    }


def is_copilot_byok_unsupported_provider_error(error: object) -> bool:
    if not isinstance(error, ValueError):
        return False
    message = str(error)
    return message in {
        COPILOT_BYOK_PROVIDER_ERROR,
        COPILOT_BYOK_TRANSPORT_POLICY_ERROR,
        COPILOT_BYOK_ENDPOINT_POLICY_ERROR,
    }


def supports_copilot_byok_provider_shape(
    model: dict[str, Any],
) -> bool:
    if not _read_string(model.get("base_url")) or _has_unsupported_transport_policy(model):
        return False
    try:
        base_url = _read_string(model.get("base_url"))
        assert base_url is not None
        _resolve_provider_type(
            (_read_string(model.get("api")) or "openai-responses").lower(),
            base_url,
            model.get("azure_api_version"),
        )
        _assert_byok_endpoint_host_allowed(base_url)
        return True
    except ValueError:
        return False


def _has_unsupported_transport_policy(model: dict[str, Any]) -> bool:
    return (
        model.get("request_proxy") is not None
        or model.get("request_tls") is not None
        or model.get("request_allow_private_network") is not None
    )


def _assert_byok_endpoint_host_allowed(base_url: str) -> None:
    try:
        parsed = urlparse(base_url)
    except ValueError:
        raise ValueError(COPILOT_BYOK_PROVIDER_ERROR) from None
    if parsed.scheme != "https":
        raise ValueError(COPILOT_BYOK_ENDPOINT_POLICY_ERROR)
    if parsed.username or parsed.password:
        raise ValueError(COPILOT_BYOK_ENDPOINT_POLICY_ERROR)
    for key, _value in parse_qsl(parsed.query, keep_blank_values=True):
        if _normalize_credential_query_param_name(key) in _CREDENTIAL_QUERY_PARAM_NAMES:
            raise ValueError(COPILOT_BYOK_ENDPOINT_POLICY_ERROR)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if _is_blocked_hostname_or_ip(hostname):
        raise ValueError(COPILOT_BYOK_ENDPOINT_POLICY_ERROR)


def _is_query_param_separator_char(char: str) -> bool:
    if char == "+":
        return True
    if char in ("\u115f", "\u1160", "\u3164", "\uffa0"):
        return True
    category = unicodedata.category(char)
    return category[0] in ("C", "Z")


def _strip_query_param_separators(value: str) -> str:
    return "".join(char for char in value if not _is_query_param_separator_char(char))


def _normalize_credential_query_param_name(name: str) -> str:
    stripped = _strip_query_param_separators(name)
    try:
        from urllib.parse import unquote

        decoded = unquote(stripped, errors="strict")
    except Exception:
        decoded = stripped
    normalized = _strip_query_param_separators(decoded).lower().replace("-", "").replace("_", "")
    return normalized


def _assert_byok_endpoint_allowed(base_url: str) -> None:
    _assert_byok_endpoint_host_allowed(base_url)


def _resolve_provider_type(
    api: str,
    base_url: str,
    azure_api_version: str | None,
) -> dict[str, Any]:
    if api == "anthropic-messages":
        return {"type": "anthropic", "base_url": base_url}
    if api == "azure-openai-responses":
        return _resolve_azure_provider_type(base_url, azure_api_version)
    if api == "openai-responses":
        return {"type": "openai", "wire_api": "responses", "base_url": base_url}
    if api in {"openai-completions", "ollama"}:
        return {"type": "openai", "wire_api": "completions", "base_url": base_url}
    raise ValueError(COPILOT_BYOK_PROVIDER_ERROR)


def _resolve_azure_provider_type(
    base_url: str,
    api_version: str | None,
) -> dict[str, Any]:
    try:
        parsed = urlparse(base_url)
    except ValueError:
        raise ValueError(COPILOT_BYOK_PROVIDER_ERROR) from None
    if _is_open_ai_compatible_azure_responses_base_url(parsed):
        return {"type": "openai", "wire_api": "responses", "base_url": base_url}
    hostname = parsed.hostname or ""
    if not _is_traditional_azure_open_ai_host(hostname):
        raise ValueError(COPILOT_BYOK_PROVIDER_ERROR)
    normalized_base_url = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
    resolved_api_version = _read_string(api_version)
    result: dict[str, Any] = {
        "type": "azure",
        "wire_api": "responses",
        "base_url": normalized_base_url,
    }
    if resolved_api_version:
        result["azure"] = {"apiVersion": resolved_api_version}
    return result


def _is_traditional_azure_open_ai_host(hostname: str) -> bool:
    return hostname.endswith((".openai.azure.com", ".cognitiveservices.azure.com"))


def _is_open_ai_compatible_azure_responses_base_url(parsed: Any) -> bool:
    hostname = (parsed.hostname or "").lower()
    if _is_traditional_azure_open_ai_host(hostname):
        return False
    is_foundry_host = hostname.endswith(
        (".services.ai.azure.com", ".api.cognitive.microsoft.com")
    )
    if not is_foundry_host:
        return False
    normalized_path = (parsed.path or "").rstrip("/")
    return normalized_path == "/openai/v1" or normalized_path.endswith("/openai/v1")


def _stable_serialize(value: object) -> str:
    if isinstance(value, list):
        return "[" + ",".join(_stable_serialize(item) for item in value) + "]"
    if isinstance(value, dict):
        entries = sorted(value.items(), key=lambda item: item[0])
        return (
            "{"
            + ",".join(
                json.dumps(key, separators=(",", ":")) + ":" + _stable_serialize(entry)
                for key, entry in entries
            )
            + "}"
        )
    if value is None:
        return "null"
    return json.dumps(value, separators=(",", ":"))


def _read_string(value: object) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed:
            return trimmed
    return None


def _is_non_secret_api_key_marker(value: str) -> bool:
    trimmed = value.strip()
    if not trimmed:
        return False
    return (
        trimmed.startswith((_OAUTH_API_KEY_MARKER_PREFIX, _SECRETREF_ENV_HEADER_MARKER_PREFIX))
        or trimmed in _CORE_NON_SECRET_API_KEY_MARKERS
        or trimmed in _AWS_SDK_ENV_MARKERS
        or trimmed in _LEGACY_ENV_API_KEY_MARKERS
        or trimmed == _NON_ENV_SECRETREF_MARKER
    )


def _resolve_provider_credential(value: str | None) -> str | None:
    credential = _read_string(value)
    if credential and not _is_non_secret_api_key_marker(credential):
        return credential
    return None


def _resolve_provider_headers(
    headers: dict[str, str | None] | None,
) -> dict[str, str] | None:
    if not headers:
        return None
    resolved = {key: value for key, value in headers.items() if isinstance(value, str)}
    return resolved or None


def _normalize_hostname(hostname: str) -> str:
    normalized = hostname.lower().strip().rstrip(".")
    if normalized.startswith("[") and normalized.endswith("]"):
        return normalized[1:-1]
    return normalized


def _is_private_ip_address(address: str) -> bool:
    normalized = _normalize_hostname(address)
    if not normalized:
        return False
    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError:
        return ":" in normalized
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


def _is_blocked_hostname_or_ip(hostname: str) -> bool:
    normalized = _normalize_hostname(hostname)
    if not normalized:
        return False
    if normalized in _BLOCKED_HOSTNAMES:
        return True
    if normalized.endswith((".localhost", ".local", ".internal")):
        return True
    return _is_private_ip_address(normalized)
