"""Amazon Bedrock Mantle discovery and bearer-token handling."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from openclaw.packages.normalization_core import (
    is_future_date_timestamp_ms,
    normalize_lowercase_string_or_empty,
    resolve_expires_at_ms_from_duration_ms,
)
from openclaw.plugin_sdk.provider_catalog_shared import (
    ModelDefinitionConfig,
    ModelProviderConfig,
)

_log = logging.getLogger("bedrock-mantle-discovery")

DEFAULT_COST = {
    "input": 0,
    "output": 0,
    "cacheRead": 0,
    "cacheWrite": 0,
}

DEFAULT_CONTEXT_WINDOW = 32000
DEFAULT_MAX_TOKENS = 4096
DEFAULT_REFRESH_INTERVAL_SECONDS = 3600
MANTLE_IAM_TOKEN_MARKER = "__amazon_bedrock_mantle_iam__"

MANTLE_SUPPORTED_REGIONS = (
    "us-east-1",
    "us-east-2",
    "us-west-2",
    "ap-northeast-1",
    "ap-south-1",
    "ap-southeast-3",
    "eu-central-1",
    "eu-west-1",
    "eu-west-2",
    "eu-south-1",
    "eu-north-1",
    "sa-east-1",
)

REASONING_PATTERNS = (
    "thinking",
    "reasoner",
    "reasoning",
    "deepseek.r",
    "gpt-oss-120b",
    "gpt-oss-safeguard-120b",
)

MantleBearerTokenProvider = Callable[[], Awaitable[str]]
MantleBearerTokenProviderFactory = Callable[
    [dict[str, Any] | None],
    MantleBearerTokenProvider,
]

FetchFn = Callable[..., Awaitable[Any]]

_iam_token_cache: dict[str, dict[str, Any]] = {}
IAM_TOKEN_TTL_MS = 7200_000
_discovery_cache: dict[str, dict[str, Any]] = {}


def _format_error_message(error: Any) -> str:
    if isinstance(error, BaseException):
        return str(error)
    return str(error)


def _mantle_endpoint(region: str) -> str:
    return f"https://bedrock-mantle.{region}.api.aws"


def _is_supported_region(region: str) -> bool:
    return region in MANTLE_SUPPORTED_REGIONS


def _load_mantle_bearer_token_provider_factory() -> MantleBearerTokenProviderFactory:
    module = importlib.import_module("aws_bedrock_token_generator")
    get_token_provider = getattr(module, "get_token_provider", None)
    if get_token_provider is None:
        raise ImportError("aws_bedrock_token_generator.get_token_provider is unavailable")
    return get_token_provider


def resolve_mantle_bearer_token(env: dict[str, str] | None = None) -> str | None:
    """Resolve a bearer token from AWS_BEARER_TOKEN_BEDROCK when set."""
    resolved_env = env if env is not None else __import__("os").environ
    explicit_token = resolved_env.get("AWS_BEARER_TOKEN_BEDROCK", "").strip()
    return explicit_token or None


def _resolve_mantle_region(env: dict[str, str]) -> str:
    return env.get("AWS_REGION") or env.get("AWS_DEFAULT_REGION") or "us-east-1"


def _get_cached_iam_token_entry(
    region: str,
    now: float | None = None,
) -> dict[str, Any] | None:
    resolved_now = now if now is not None else __import__("time").time() * 1000
    cached = _iam_token_cache.get(region)
    if cached and is_future_date_timestamp_ms(cached["expiresAt"], now_ms=resolved_now):
        return cached
    _iam_token_cache.pop(region, None)
    return None


async def generate_bearer_token_from_iam(
    params: dict[str, Any],
) -> str | None:
    """Generate a bearer token from IAM credentials when the generator package is available."""
    now_ms = params["now"]() if callable(params.get("now")) else __import__("time").time() * 1000
    region = params["region"]
    cached = _get_cached_iam_token_entry(region, now_ms)
    if cached:
        return cached["token"]

    try:
        token_provider_factory = params.get("tokenProviderFactory")
        if token_provider_factory is None:
            token_provider_factory = _load_mantle_bearer_token_provider_factory()
        token_provider = token_provider_factory(
            {
                "region": region,
                "expiresInSeconds": 7200,
            }
        )
        token = await token_provider()
        expires_at = resolve_expires_at_ms_from_duration_ms(IAM_TOKEN_TTL_MS, now_ms=now_ms)
        if expires_at is not None:
            _iam_token_cache[region] = {"token": token, "expiresAt": expires_at}
        return token
    except Exception as error:  # noqa: BLE001
        _log.debug(
            "Mantle IAM token generation unavailable",
            extra={"region": region, "error": _format_error_message(error)},
        )
        return None


def get_cached_iam_token(region: str) -> str | None:
    """Read a cached IAM bearer token for the given region without generating one."""
    cached = _get_cached_iam_token_entry(region)
    return cached["token"] if cached else None


async def resolve_mantle_runtime_bearer_token(
    params: dict[str, Any],
) -> dict[str, Any] | None:
    """Resolve the runtime bearer token, generating IAM tokens when needed."""
    api_key = params["apiKey"]
    if api_key != MANTLE_IAM_TOKEN_MARKER:
        return {"apiKey": api_key}

    env = params.get("env") if isinstance(params.get("env"), dict) else __import__("os").environ
    now_ms = params["now"]() if callable(params.get("now")) else __import__("time").time() * 1000
    region = _resolve_mantle_region(env)
    cached = _get_cached_iam_token_entry(region, now_ms)
    if cached:
        return {
            "apiKey": cached["token"],
            "expiresAt": cached["expiresAt"],
        }

    token = await generate_bearer_token_from_iam(
        {
            "region": region,
            "now": params.get("now"),
            "tokenProviderFactory": params.get("tokenProviderFactory"),
        }
    )
    if not token:
        return None

    refreshed = _get_cached_iam_token_entry(region, now_ms)
    expires_at = (
        refreshed["expiresAt"]
        if refreshed
        else resolve_expires_at_ms_from_duration_ms(IAM_TOKEN_TTL_MS, now_ms=now_ms)
    )
    result: dict[str, Any] = {"apiKey": refreshed["token"] if refreshed else token}
    if expires_at is not None:
        result["expiresAt"] = expires_at
    return result


def reset_iam_token_cache_for_test() -> None:
    """Clear the IAM token cache for tests."""
    _iam_token_cache.clear()


def reset_mantle_discovery_cache_for_test() -> None:
    """Clear the Mantle discovery cache for tests."""
    _discovery_cache.clear()


def _infer_reasoning_support(model_id: str) -> bool:
    lower = normalize_lowercase_string_or_empty(model_id)
    return any(pattern in lower for pattern in REASONING_PATTERNS)


async def _default_fetch_fn(url: str, init: dict[str, Any]) -> Any:
    headers = init.get("headers") if isinstance(init.get("headers"), dict) else {}
    method = str(init.get("method", "GET")).upper()
    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=headers)
        return _HttpxFetchResponse(response)


class _HttpxFetchResponse:
    def __init__(self, response: httpx.Response) -> None:
        self.ok = response.is_success
        self.status = response.status_code
        self.statusText = response.reason_phrase or ""
        self._response = response

    async def json(self) -> Any:
        return self._response.json()


async def discover_mantle_models(params: dict[str, Any]) -> list[ModelDefinitionConfig]:
    """Discover available models from the Mantle /v1/models endpoint."""
    region = params["region"]
    bearer_token = params["bearerToken"]
    fetch_fn = params.get("fetchFn") or _default_fetch_fn
    now_fn = params.get("now")
    now_ms = now_fn() if callable(now_fn) else __import__("time").time() * 1000

    cache_key = region
    cached = _discovery_cache.get(cache_key)
    if cached and now_ms - cached["fetchedAt"] < DEFAULT_REFRESH_INTERVAL_SECONDS * 1000:
        return cached["models"]

    endpoint = f"{_mantle_endpoint(region)}/v1/models"

    try:
        response = await fetch_fn(
            endpoint,
            {
                "method": "GET",
                "headers": {
                    "Authorization": f"Bearer {bearer_token}",
                    "Accept": "application/json",
                },
            },
        )

        if not response.ok:
            _log.debug(
                "Mantle model discovery failed",
                extra={"status": response.status, "statusText": response.statusText},
            )
            return cached["models"] if cached else []

        body = await response.json()
        raw_models = body.get("data", []) if isinstance(body, dict) else []

        models: list[ModelDefinitionConfig] = []
        for entry in raw_models:
            if not isinstance(entry, dict):
                continue
            model_id = str(entry.get("id", "")).strip()
            if not model_id:
                continue
            models.append(
                {
                    "id": model_id,
                    "name": model_id,
                    "reasoning": _infer_reasoning_support(model_id),
                    "input": ["text"],
                    "cost": dict(DEFAULT_COST),
                    "contextWindow": DEFAULT_CONTEXT_WINDOW,
                    "maxTokens": DEFAULT_MAX_TOKENS,
                }
            )

        models.sort(key=lambda model: model["id"])
        _discovery_cache[cache_key] = {"models": models, "fetchedAt": now_ms}
        return models
    except Exception as error:  # noqa: BLE001
        _log.debug(
            "Mantle model discovery error",
            extra={"error": _format_error_message(error)},
        )
        return cached["models"] if cached else []


async def resolve_implicit_mantle_provider(
    params: dict[str, Any] | None = None,
) -> ModelProviderConfig | None:
    """Resolve implicit Mantle provider config from env, IAM token support, and discovery."""
    resolved_params = params or {}
    env = resolved_params.get("env") if isinstance(resolved_params.get("env"), dict) else __import__(
        "os"
    ).environ
    plugin_config = resolved_params.get("pluginConfig")
    if (
        isinstance(plugin_config, dict)
        and isinstance(plugin_config.get("discovery"), dict)
        and plugin_config["discovery"].get("enabled") is False
    ):
        return None

    region = _resolve_mantle_region(env)
    explicit_bearer_token = resolve_mantle_bearer_token(env)

    if not _is_supported_region(region):
        _log.debug("Mantle not available in region", extra={"region": region})
        return None

    bearer_token = explicit_bearer_token
    if not bearer_token:
        bearer_token = await generate_bearer_token_from_iam(
            {
                "region": region,
                "tokenProviderFactory": resolved_params.get("tokenProviderFactory"),
            }
        )

    if not bearer_token:
        return None

    models = await discover_mantle_models(
        {
            "region": region,
            "bearerToken": bearer_token,
            "fetchFn": resolved_params.get("fetchFn"),
        }
    )

    if not models:
        return None

    _log.debug(
        "Mantle provider resolved",
        extra={"region": region, "modelCount": len(models)},
    )

    claude_models: list[ModelDefinitionConfig] = [
        {
            "id": "anthropic.claude-opus-4-7",
            "name": "Claude Opus 4.7",
            "api": "anthropic-messages",
            "reasoning": False,
            "input": ["text", "image"],
            "cost": {
                "input": 5,
                "output": 25,
                "cacheRead": 0.5,
                "cacheWrite": 6.25,
            },
            "contextWindow": 1_000_000,
            "maxTokens": 128_000,
        },
        {
            "id": "anthropic.claude-mythos-preview",
            "name": "Claude Mythos Preview",
            "api": "anthropic-messages",
            "reasoning": True,
            "params": {"canonicalModelId": "claude-mythos-preview"},
            "input": ["text", "image"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            "contextWindow": 1_000_000,
            "maxTokens": 128_000,
        },
    ]
    all_models = [*models, *claude_models]

    return {
        "baseUrl": f"{_mantle_endpoint(region)}/v1",
        "api": "openai-completions",
        "auth": "api-key",
        "apiKey": (
            "env:AWS_BEARER_TOKEN_BEDROCK" if explicit_bearer_token else MANTLE_IAM_TOKEN_MARKER
        ),
        "models": all_models,
    }


def merge_implicit_mantle_provider(params: dict[str, Any]) -> ModelProviderConfig:
    """Merge an implicit Mantle provider catalog with explicit user config."""
    existing = params.get("existing")
    implicit = params["implicit"]
    if not existing:
        return implicit

    existing_models = existing.get("models")
    return {
        **implicit,
        **existing,
        "models": (
            existing_models
            if isinstance(existing_models, list) and len(existing_models) > 0
            else implicit.get("models")
        ),
    }
