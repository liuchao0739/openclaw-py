from __future__ import annotations

import re
from typing import Any, Callable

from openclaw.plugin_sdk.core import create_subsystem_logger
from openclaw.plugin_sdk.error_runtime import format_error_message
from openclaw.plugin_sdk.number_runtime import (
    is_future_date_timestamp_ms,
    resolve_expires_at_ms_from_duration_seconds,
)
from openclaw.plugin_sdk.provider_model_shared import (
    BedrockDiscoveryConfig,
    ModelDefinitionConfig,
    ModelProviderConfig,
    resolve_claude_fable5_model_identity,
    resolve_claude_model_identity,
    supports_claude_adaptive_thinking,
)
from openclaw.plugin_sdk.string_coerce_runtime import (
    normalize_lowercase_string_or_empty,
    normalize_optional_lowercase_string,
)
from openclaw_extensions.amazon_bedrock.aws_credential_refresh import (
    refresh_aws_shared_config_cache_for_bedrock,
)
from openclaw_extensions.amazon_bedrock.discovery_shared import (
    resolve_bedrock_config_api_key,
)
from openclaw_extensions.amazon_bedrock.thinking_policy import (
    resolve_bedrock_native_thinking_level_map,
)

log = create_subsystem_logger("bedrock-discovery")

_DEFAULT_REFRESH_INTERVAL_SECONDS = 3600
_DEFAULT_CONTEXT_WINDOW = 32_000
_DEFAULT_MAX_TOKENS = 4096

_KNOWN_CONTEXT_WINDOWS: dict[str, int] = {
    "anthropic.claude-fable-5": 1_000_000,
    "anthropic.claude-3-7-sonnet-20250219-v1:0": 200_000,
    "anthropic.claude-opus-4-8": 1_000_000,
    "anthropic.claude-opus-4-7": 1_000_000,
    "anthropic.claude-opus-4-6-v1": 1_000_000,
    "anthropic.claude-opus-4-6-v1:0": 1_000_000,
    "anthropic.claude-sonnet-4-6": 1_000_000,
    "anthropic.claude-sonnet-4-6-v1:0": 1_000_000,
    "anthropic.claude-sonnet-4-5-20250929-v1:0": 200_000,
    "anthropic.claude-sonnet-4-20250514-v1:0": 200_000,
    "anthropic.claude-opus-4-5-20251101-v1:0": 200_000,
    "anthropic.claude-opus-4-1-20250805-v1:0": 200_000,
    "anthropic.claude-haiku-4-5-20251001-v1:0": 200_000,
    "anthropic.claude-3-5-haiku-20241022-v1:0": 200_000,
    "anthropic.claude-3-haiku-20240307-v1:0": 200_000,
    "amazon.nova-premier-v1:0": 1_000_000,
    "amazon.nova-pro-v1:0": 300_000,
    "amazon.nova-lite-v1:0": 300_000,
    "amazon.nova-micro-v1:0": 128_000,
    "amazon.nova-2-lite-v1:0": 300_000,
    "minimax.minimax-m2.5": 1_000_000,
    "minimax.minimax-m2.1": 1_000_000,
    "minimax.minimax-m2": 1_000_000,
    "meta.llama4-maverick-17b-instruct-v1:0": 1_000_000,
    "meta.llama4-scout-17b-instruct-v1:0": 512_000,
    "meta.llama3-3-70b-instruct-v1:0": 128_000,
    "meta.llama3-2-90b-instruct-v1:0": 128_000,
    "meta.llama3-2-11b-instruct-v1:0": 128_000,
    "meta.llama3-2-3b-instruct-v1:0": 128_000,
    "meta.llama3-2-1b-instruct-v1:0": 128_000,
    "meta.llama3-1-405b-instruct-v1:0": 128_000,
    "meta.llama3-1-70b-instruct-v1:0": 128_000,
    "meta.llama3-1-8b-instruct-v1:0": 128_000,
    "nvidia.nemotron-super-3-120b": 256_000,
    "nvidia.nemotron-nano-3-30b": 128_000,
    "nvidia.nemotron-nano-12b-v2": 128_000,
    "nvidia.nemotron-nano-9b-v2": 128_000,
    "mistral.mistral-large-3-675b-instruct": 128_000,
    "mistral.mistral-large-2407-v1:0": 128_000,
    "mistral.mistral-small-2402-v1:0": 32_000,
    "deepseek.r1-v1:0": 128_000,
    "deepseek.v3.2": 128_000,
    "cohere.command-r-plus-v1:0": 128_000,
    "cohere.command-r-v1:0": 128_000,
    "ai21.jamba-1-5-large-v1:0": 256_000,
    "ai21.jamba-1-5-mini-v1:0": 256_000,
    "google.gemma-3-27b-it": 128_000,
    "google.gemma-3-12b-it": 128_000,
    "google.gemma-3-4b-it": 128_000,
    "zai.glm-5": 128_000,
    "zai.glm-4.7": 128_000,
    "zai.glm-4.7-flash": 128_000,
    "qwen.qwen3-coder-next": 256_000,
    "qwen.qwen3-coder-30b-a3b-v1:0": 256_000,
    "qwen.qwen3-32b-v1:0": 128_000,
    "qwen.qwen3-vl-235b-a22b": 128_000,
}

_DEFAULT_COST = {
    "input": 0,
    "output": 0,
    "cacheRead": 0,
    "cacheWrite": 0,
}

_discovery_cache: dict[str, dict[str, Any]] = {}
_has_logged_bedrock_error = False


def _resolve_known_context_window(model_id: str) -> int | None:
    stripped = re.sub(r"^(?:us|eu|ap|apac|au|jp|global)\.", "", model_id)
    candidates = [model_id, stripped]
    for candidate in candidates:
        if resolve_claude_fable5_model_identity({"id": candidate}):
            return 1_000_000
        if re.search(r"(?:^|[/.:])anthropic\.claude-opus-4[.-]8(?:$|[-.:/])", candidate, re.IGNORECASE):
            return 1_000_000
        if candidate in _KNOWN_CONTEXT_WINDOWS:
            return _KNOWN_CONTEXT_WINDOWS[candidate]
        without_version_suffix = re.sub(r":0$", "", candidate)
        if without_version_suffix != candidate and without_version_suffix in _KNOWN_CONTEXT_WINDOWS:
            return _KNOWN_CONTEXT_WINDOWS[without_version_suffix]
    return None


def _is_known_claude_mythos_preview_model_id(model_id: str) -> bool:
    stripped = re.sub(r"^(?:us|eu|ap|apac|au|jp|global)\.", "", model_id)
    return any(
        re.search(r"(?:^|[/.:])anthropic\.claude-mythos-preview(?:$|[-.:/])", candidate, re.IGNORECASE)
        for candidate in [model_id, stripped]
    )


def _resolve_known_thinking_level_map(model_id: str) -> dict[str, Any] | None:
    return resolve_bedrock_native_thinking_level_map(model_id)


def _resolve_known_max_tokens(model_id: str) -> int | None:
    return 128_000 if resolve_claude_fable5_model_identity({"id": model_id}) else None


def _normalize_provider_filter(filter_list: list[str] | None) -> list[str]:
    if not filter_list:
        return []
    normalized = {
        normalize_optional_lowercase_string(entry)
        for entry in filter_list
        if normalize_optional_lowercase_string(entry)
    }
    return sorted(normalized)


def _build_cache_key(params: dict[str, Any]) -> str:
    import json
    return json.dumps(params, sort_keys=True)


def _includes_text_modalities(modalities: list[str] | None) -> bool:
    if not modalities:
        return False
    return any(normalize_optional_lowercase_string(entry) == "text" for entry in modalities)


def _is_active(summary: dict[str, Any]) -> bool:
    status = summary.get("modelLifecycle", {}).get("status") if isinstance(summary.get("modelLifecycle"), dict) else None
    return status is not None and isinstance(status, str) and status.upper() == "ACTIVE"


def _map_input_modalities(summary: dict[str, Any]) -> list[str]:
    inputs = summary.get("inputModalities") or []
    mapped: set[str] = set()
    for modality in inputs:
        lower = normalize_optional_lowercase_string(modality)
        if lower == "text":
            mapped.add("text")
        if lower == "image":
            mapped.add("image")
    if not mapped:
        mapped.add("text")
    return sorted(mapped)


def _infer_reasoning_support(summary: dict[str, Any]) -> bool:
    if supports_claude_adaptive_thinking({"id": summary.get("modelId", "")}):
        return True
    haystack = normalize_lowercase_string_or_empty(
        f"{summary.get('modelId', '')} {summary.get('modelName', '')}"
    )
    return "reasoning" in haystack or "thinking" in haystack


def _resolve_default_context_window(config: BedrockDiscoveryConfig | None) -> int:
    raw = config.get("defaultContextWindow") if config else None
    value = int(raw) if raw is not None else _DEFAULT_CONTEXT_WINDOW
    return value if value > 0 else _DEFAULT_CONTEXT_WINDOW


def _resolve_default_max_tokens(config: BedrockDiscoveryConfig | None) -> int:
    raw = config.get("defaultMaxTokens") if config else None
    value = int(raw) if raw is not None else _DEFAULT_MAX_TOKENS
    return value if value > 0 else _DEFAULT_MAX_TOKENS


def _matches_provider_filter(summary: dict[str, Any], filter_list: list[str]) -> bool:
    if not filter_list:
        return True
    provider_name = summary.get("providerName")
    if provider_name is None:
        model_id = summary.get("modelId", "")
        provider_name = model_id.split(".")[0] if model_id else None
    normalized = normalize_optional_lowercase_string(provider_name)
    if not normalized:
        return False
    return normalized in filter_list


def _should_include_summary(summary: dict[str, Any], filter_list: list[str]) -> bool:
    model_id = summary.get("modelId", "")
    if not model_id or not model_id.strip():
        return False
    if not _matches_provider_filter(summary, filter_list):
        return False
    if summary.get("responseStreamingSupported") is not True:
        return False
    if _is_known_claude_mythos_preview_model_id(model_id):
        return False
    output_modalities = summary.get("outputModalities")
    if not _includes_text_modalities(output_modalities if isinstance(output_modalities, list) else None):
        return False
    if not _is_active(summary):
        return False
    return True


def _to_model_definition(
    summary: dict[str, Any],
    defaults: dict[str, int],
) -> dict[str, Any]:
    model_id = (summary.get("modelId") or "").strip()
    thinking_level_map = _resolve_known_thinking_level_map(model_id)
    result: dict[str, Any] = {
        "id": model_id,
        "name": (summary.get("modelName") or "").strip() or model_id,
        "reasoning": _infer_reasoning_support(summary),
        "input": _map_input_modalities(summary),
        "cost": dict(_DEFAULT_COST),
        "contextWindow": _resolve_known_context_window(model_id) or defaults["contextWindow"],
        "maxTokens": _resolve_known_max_tokens(model_id) or defaults["maxTokens"],
    }
    if thinking_level_map is not None:
        result["thinkingLevelMap"] = thinking_level_map
    return result


def _resolve_base_model_id(profile: dict[str, Any]) -> str | None:
    models = profile.get("models")
    if models and len(models) > 0:
        first_arn = models[0].get("modelArn")
        if first_arn:
            match = re.search(r"foundation-model/(.+)$", first_arn)
            if match:
                return match.group(1)
    if profile.get("type") == "SYSTEM_DEFINED":
        profile_id = profile.get("inferenceProfileId", "")
        prefix_match = re.match(r"^(?:us|eu|ap|apac|au|jp|global)\.(.+)$", profile_id, re.IGNORECASE)
        if prefix_match:
            return prefix_match.group(1)
    return None


async def _fetch_inference_profile_summaries(
    client: Any,
    create_list_fn: Callable[[dict[str, Any]], Any],
) -> list[dict[str, Any]]:
    try:
        profiles: list[dict[str, Any]] = []
        next_token: str | None = None
        while True:
            response = client.send(create_list_fn({"nextToken": next_token}))
            for summary in (response.get("inferenceProfileSummaries") or []):
                profiles.append(summary)
            next_token = response.get("nextToken")
            if not next_token:
                break
        return profiles
    except Exception as e:
        if log:
            log.debug(f"Skipping inference profile discovery: {format_error_message(e)}")
        return []


def _resolve_inference_profiles(
    profiles: list[dict[str, Any]],
    defaults: dict[str, int],
    provider_filter: list[str],
    foundation_models: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    for profile in profiles:
        profile_id = (profile.get("inferenceProfileId") or "").strip()
        if not profile_id:
            continue
        if profile.get("status") != "ACTIVE":
            continue

        if provider_filter:
            models = profile.get("models") or []
            matches_filter = False
            for m in models:
                provider = (m.get("modelArn") or "").split("/")[-1].split(".")[0] if m.get("modelArn") else ""
                if provider and normalize_optional_lowercase_string(provider) in provider_filter:
                    matches_filter = True
                    break
            if not matches_filter:
                continue

        base_model_id = _resolve_base_model_id(profile)
        check_id = base_model_id or profile_id
        if _is_known_claude_mythos_preview_model_id(check_id):
            continue

        base_model = None
        if base_model_id:
            base_model = foundation_models.get(normalize_lowercase_string_or_empty(base_model_id))

        known_thinking_level_map = _resolve_known_thinking_level_map(check_id)
        canonical_claude_id = resolve_claude_model_identity({"id": base_model_id}) if base_model_id else ""

        entry: dict[str, Any] = {
            "id": profile_id,
            "name": (profile.get("inferenceProfileName") or "").strip() or profile_id,
            "reasoning": (
                base_model.get("reasoning")
                if base_model
                else supports_claude_adaptive_thinking({"id": check_id})
            ),
            "input": base_model.get("input") if base_model else ["text"],
            "cost": base_model.get("cost") if base_model else dict(_DEFAULT_COST),
            "contextWindow": (
                base_model.get("contextWindow")
                if base_model
                else _resolve_known_context_window(check_id) or defaults["contextWindow"]
            ),
            "maxTokens": (
                base_model.get("maxTokens")
                if base_model
                else _resolve_known_max_tokens(check_id) or defaults["maxTokens"]
            ),
        }
        thinking_map = base_model.get("thinkingLevelMap") if base_model else known_thinking_level_map
        if thinking_map is not None:
            entry["thinkingLevelMap"] = thinking_map
        if canonical_claude_id and canonical_claude_id.startswith("claude-"):
            entry["params"] = {"canonicalModelId": canonical_claude_id}

        discovered.append(entry)
    return discovered


def reset_bedrock_discovery_cache_for_test() -> None:
    global _has_logged_bedrock_error
    _discovery_cache.clear()
    _has_logged_bedrock_error = False


async def discover_bedrock_models(params: dict[str, Any]) -> list[dict[str, Any]]:
    region = params["region"]
    config = params.get("config")
    now_fn = params.get("now")
    client_factory = params.get("clientFactory")

    refresh_interval_seconds = max(
        0,
        int(config.get("refreshInterval", _DEFAULT_REFRESH_INTERVAL_SECONDS)) if config else _DEFAULT_REFRESH_INTERVAL_SECONDS,
    )
    provider_filter = _normalize_provider_filter(config.get("providerFilter") if config else None)
    default_context_window = _resolve_default_context_window(config)
    default_max_tokens = _resolve_default_max_tokens(config)

    cache_key = _build_cache_key({
        "region": region,
        "providerFilter": provider_filter,
        "refreshIntervalSeconds": refresh_interval_seconds,
        "defaultContextWindow": default_context_window,
        "defaultMaxTokens": default_max_tokens,
    })
    now = now_fn() if now_fn else int(__import__("time").time() * 1000)

    if refresh_interval_seconds > 0:
        cached = _discovery_cache.get(cache_key)
        if cached and is_future_date_timestamp_ms(cached["expiresAt"], now_ms=now):
            if "value" in cached and cached["value"] is not None:
                return cached["value"]
            if "inFlight" in cached and cached["inFlight"] is not None:
                return await cached["inFlight"]
        if cached:
            del _discovery_cache[cache_key]

    if client_factory:
        from openclaw_extensions.amazon_bedrock.aws_credential_refresh import (
            refresh_aws_shared_config_cache_for_bedrock,
        )
        await refresh_aws_shared_config_cache_for_bedrock()

    discovery_promise = _do_discover_bedrock_models(
        region=region,
        client_factory=client_factory,
        provider_filter=provider_filter,
        default_context_window=default_context_window,
        default_max_tokens=default_max_tokens,
    )

    if refresh_interval_seconds > 0:
        expires_at = resolve_expires_at_ms_from_duration_seconds(refresh_interval_seconds, now_ms=now)
        if expires_at is not None:
            _discovery_cache[cache_key] = {
                "expiresAt": expires_at,
                "inFlight": discovery_promise,
            }

    try:
        value = await discovery_promise
        if refresh_interval_seconds > 0:
            expires_at = resolve_expires_at_ms_from_duration_seconds(refresh_interval_seconds, now_ms=now)
            if expires_at is not None:
                _discovery_cache[cache_key] = {
                    "expiresAt": expires_at,
                    "value": value,
                }
        return value
    except Exception as e:
        if refresh_interval_seconds > 0:
            _discovery_cache.pop(cache_key, None)
        if not _has_logged_bedrock_error:
            global _has_logged_bedrock_error
            _has_logged_bedrock_error = True
            if log:
                log.warn(f"Failed to discover Bedrock models: {format_error_message(e)}")
        return []


async def _do_discover_bedrock_models(
    region: str,
    client_factory: Callable[[str], Any] | None,
    provider_filter: list[str],
    default_context_window: int,
    default_max_tokens: int,
) -> list[dict[str, Any]]:
    if client_factory is None:
        raise ValueError("client_factory is required for Bedrock discovery")
    client = client_factory(region)

    raw_foundation_response = client.list_foundation_models()
    profile_summaries = client.list_inference_profiles()

    discovered: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    foundation_models: dict[str, dict[str, Any]] = {}

    for summary in raw_foundation_response.get("modelSummaries", []) or []:
        if not _should_include_summary(summary, provider_filter):
            continue
        model_def = _to_model_definition(summary, {
            "contextWindow": default_context_window,
            "maxTokens": default_max_tokens,
        })
        discovered.append(model_def)
        normalized_id = normalize_lowercase_string_or_empty(model_def["id"])
        seen_ids.add(normalized_id)
        foundation_models[normalized_id] = model_def

    inference_profiles = _resolve_inference_profiles(
        profile_summaries,
        {"contextWindow": default_context_window, "maxTokens": default_max_tokens},
        provider_filter,
        foundation_models,
    )
    for profile in inference_profiles:
        normalized_id = normalize_lowercase_string_or_empty(profile["id"])
        if normalized_id not in seen_ids:
            discovered.append(profile)
            seen_ids.add(normalized_id)

    discovered.sort(key=lambda a: (0 if str(a.get("id", "")).startswith("global.") else 1, str(a.get("name", ""))))
    return discovered


async def resolve_implicit_bedrock_provider(params: dict[str, Any]) -> dict[str, Any] | None:
    import os as _os
    env = params.get("env") or _os.environ
    plugin_config = params.get("pluginConfig")
    client_factory = params.get("clientFactory")

    discovery_config = plugin_config.get("discovery") if plugin_config else None
    enabled = discovery_config.get("enabled") if discovery_config else None
    has_aws_creds = resolve_bedrock_config_api_key(env) is not None

    if enabled is False:
        return None
    if enabled is not True and not has_aws_creds:
        return None

    region = (
        (discovery_config or {}).get("region")
        or env.get("AWS_REGION")
        or env.get("AWS_DEFAULT_REGION")
        or "us-east-1"
    )

    models = await discover_bedrock_models({
        "region": region,
        "config": discovery_config,
        "clientFactory": client_factory,
    })
    if not models:
        return None

    return {
        "baseUrl": f"https://bedrock-runtime.{region}.amazonaws.com",
        "api": "bedrock-converse-stream",
        "auth": "aws-sdk",
        "models": models,
    }


__all__ = [
    "discover_bedrock_models",
    "reset_bedrock_discovery_cache_for_test",
    "resolve_implicit_bedrock_provider",
]