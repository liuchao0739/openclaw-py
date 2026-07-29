import asyncio
import logging
import os
import re
import time
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional

log = logging.getLogger("bedrock-mantle-discovery")

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


def mantle_endpoint(region: str) -> str:
    return f"https://bedrock-mantle.{region}.api.aws"


def is_supported_region(region: str) -> bool:
    return region in MANTLE_SUPPORTED_REGIONS


MantleBearerTokenProvider = Callable[[], Awaitable[str]]
MantleBearerTokenProviderFactory = Callable[..., MantleBearerTokenProvider]


async def load_mantle_bearer_token_provider_factory() -> MantleBearerTokenProviderFactory:
    try:
        from aws_bedrock_token_generator import get_token_provider
    except ImportError:
        raise RuntimeError("@aws/bedrock-token-generator is not installed")
    return get_token_provider


def _get_env(env: Optional[Mapping[str, str]] = None) -> Mapping[str, str]:
    return env if env is not None else os.environ


def resolve_mantle_bearer_token(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    source = _get_env(env)
    explicit_token = (source.get("AWS_BEARER_TOKEN_BEDROCK") or "").strip()
    if explicit_token:
        return explicit_token
    return None


iam_token_cache: Dict[str, Dict[str, Any]] = {}
IAM_TOKEN_TTL_MS = 7200_000


def resolve_mantle_region(env: Optional[Mapping[str, str]] = None) -> str:
    source = _get_env(env)
    return source.get("AWS_REGION") or source.get("AWS_DEFAULT_REGION") or "us-east-1"


def _is_future_timestamp_ms(expires_at: float, now_ms: float) -> bool:
    return expires_at > now_ms


def get_cached_iam_token_entry(
    region: str, now: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    cached = iam_token_cache.get(region)
    if cached and _is_future_timestamp_ms(cached["expiresAt"], now if now is not None else time.time() * 1000):
        return cached
    iam_token_cache.pop(region, None)
    return None


async def generate_bearer_token_from_iam(params: Dict[str, Any]) -> Optional[str]:
    now_ms = (params["now"]() if params.get("now") else time.time() * 1000)
    cached = get_cached_iam_token_entry(params["region"], now_ms)
    if cached:
        return cached["token"]

    try:
        token_provider_factory = params.get("tokenProviderFactory") or (
            await load_mantle_bearer_token_provider_factory()
        )
        token_provider = token_provider_factory(
            region=params["region"], expiresInSeconds=7200
        )
        token = await token_provider()
        expires_at = now_ms + IAM_TOKEN_TTL_MS
        iam_token_cache[params["region"]] = {"token": token, "expiresAt": expires_at}
        return token
    except Exception as error:
        log.debug("Mantle IAM token generation unavailable: %s", error)
        return None


def get_cached_iam_token(region: str) -> Optional[str]:
    entry = get_cached_iam_token_entry(region)
    return entry["token"] if entry else None


async def resolve_mantle_runtime_bearer_token(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if params["apiKey"] != MANTLE_IAM_TOKEN_MARKER:
        return {"apiKey": params["apiKey"]}

    now_ms = (params["now"]() if params.get("now") else time.time() * 1000)
    region = resolve_mantle_region(params.get("env"))
    cached = get_cached_iam_token_entry(region, now_ms)
    if cached:
        return {"apiKey": cached["token"], "expiresAt": cached["expiresAt"]}

    token = await generate_bearer_token_from_iam(
        {
            "region": region,
            "now": params.get("now"),
            "tokenProviderFactory": params.get("tokenProviderFactory"),
        }
    )
    if not token:
        return None

    refreshed = get_cached_iam_token_entry(region, now_ms)
    expires_at = (refreshed["expiresAt"] if refreshed else now_ms + IAM_TOKEN_TTL_MS)
    return {
        "apiKey": refreshed["token"] if refreshed else token,
        "expiresAt": expires_at,
    }


def reset_iam_token_cache_for_test() -> None:
    iam_token_cache.clear()


REASONING_PATTERNS = (
    "thinking",
    "reasoner",
    "reasoning",
    "deepseek.r",
    "gpt-oss-120b",
    "gpt-oss-safeguard-120b",
)


def infer_reasoning_support(model_id: str) -> bool:
    lower = (model_id or "").lower()
    return any(pattern in lower for pattern in REASONING_PATTERNS)


discovery_cache: Dict[str, Dict[str, Any]] = {}


def reset_mantle_discovery_cache_for_test() -> None:
    discovery_cache.clear()


async def discover_mantle_models(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    region = params["region"]
    bearer_token = params["bearerToken"]
    fetch_fn = params.get("fetchFn")
    now_ms = (params["now"]() if params.get("now") else time.time() * 1000)

    cache_key = region
    cached = discovery_cache.get(cache_key)
    if cached and now_ms - cached["fetchedAt"] < DEFAULT_REFRESH_INTERVAL_SECONDS * 1000:
        return cached["models"]

    endpoint = f"{mantle_endpoint(region)}/v1/models"

    try:
        if fetch_fn is None:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {bearer_token}",
                        "Accept": "application/json",
                    },
                ) as response:
                    if response.status >= 400:
                        log.debug("Mantle model discovery failed: %s", response.status)
                        return cached.get("models", []) if cached else []
                    body = await response.json()
        else:
            response = await fetch_fn(
                endpoint,
                method="GET",
                headers={
                    "Authorization": f"Bearer {bearer_token}",
                    "Accept": "application/json",
                },
            )
            if not response.get("ok"):
                log.debug("Mantle model discovery failed: %s", response.get("status"))
                return cached.get("models", []) if cached else []
            body = response.get("json") or {}

        raw_models = body.get("data") or []

        models = [
            {
                "id": m["id"],
                "name": m["id"],
                "reasoning": infer_reasoning_support(m["id"]),
                "input": ["text"],
                "cost": dict(DEFAULT_COST),
                "contextWindow": DEFAULT_CONTEXT_WINDOW,
                "maxTokens": DEFAULT_MAX_TOKENS,
            }
            for m in raw_models
            if (m.get("id") or "").strip()
        ]
        models.sort(key=lambda model: model["id"])

        discovery_cache[cache_key] = {"models": models, "fetchedAt": now_ms}
        return models
    except Exception as error:
        log.debug("Mantle model discovery error: %s", error)
        return cached.get("models", []) if cached else []


async def resolve_implicit_mantle_provider(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    env = _get_env(params.get("env"))
    plugin_config = params.get("pluginConfig") or {}
    if plugin_config.get("discovery", {}).get("enabled") is False:
        return None

    region = resolve_mantle_region(env)
    explicit_bearer_token = resolve_mantle_bearer_token(env)

    if not is_supported_region(region):
        log.debug("Mantle not available in region: %s", region)
        return None

    bearer_token = explicit_bearer_token
    if not bearer_token:
        bearer_token = await generate_bearer_token_from_iam(
            {
                "region": region,
                "tokenProviderFactory": params.get("tokenProviderFactory"),
            }
        )

    if not bearer_token:
        return None

    models = await discover_mantle_models(
        {
            "region": region,
            "bearerToken": bearer_token,
            "fetchFn": params.get("fetchFn"),
        }
    )

    if not models:
        return None

    log.debug("Mantle provider resolved: region=%s models=%s", region, len(models))

    claude_models = [
        {
            "id": "anthropic.claude-opus-4-7",
            "name": "Claude Opus 4.7",
            "api": "anthropic-messages",
            "reasoning": False,
            "input": ["text", "image"],
            "cost": {"input": 5, "output": 25, "cacheRead": 0.5, "cacheWrite": 6.25},
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
    all_models = list(models) + claude_models

    return {
        "baseUrl": f"{mantle_endpoint(region)}/v1",
        "api": "openai-completions",
        "auth": "api-key",
        "apiKey": "env:AWS_BEARER_TOKEN_BEDROCK" if explicit_bearer_token else MANTLE_IAM_TOKEN_MARKER,
        "models": all_models,
    }


def merge_implicit_mantle_provider(params: Dict[str, Any]) -> Dict[str, Any]:
    existing = params.get("existing")
    implicit = params["implicit"]
    if not existing:
        return implicit

    merged = dict(implicit)
    merged.update(existing)
    existing_models = existing.get("models")
    if isinstance(existing_models, list) and len(existing_models) > 0:
        merged["models"] = existing_models
    else:
        merged["models"] = implicit["models"]
    return merged
