from __future__ import annotations

import re
from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw.plugin_sdk.llm_runtime import register_api_provider
from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi
from openclaw.plugin_sdk.provider_model_shared import (
    ANTHROPIC_BY_MODEL_REPLAY_HOOKS,
    normalize_provider_id,
    resolve_claude_fable5_model_identity,
    resolve_claude_model_identity,
)
from openclaw.plugin_sdk.provider_stream_shared import stream_with_payload_patch
from openclaw.plugin_sdk.llm_runtime import stream_simple as _stream_simple
from openclaw_extensions.amazon_bedrock.aws_credential_refresh import (
    refresh_aws_shared_config_cache_for_bedrock,
)
from openclaw_extensions.amazon_bedrock.bedrock_options import (
    supports_bedrock_prompt_caching,
)
from openclaw_extensions.amazon_bedrock.discovery_shared import (
    merge_implicit_bedrock_provider,
    resolve_bedrock_config_api_key,
)
from openclaw_extensions.amazon_bedrock.memory_embedding_adapter import (
    bedrock_memory_embedding_provider_adapter,
)
from openclaw_extensions.amazon_bedrock.stream_runtime import (
    stream_bedrock,
    stream_simple_bedrock,
)
from openclaw_extensions.amazon_bedrock.thinking_policy import (
    is_latest_adaptive_bedrock_model_ref,
    is_opus47_or_newer_bedrock_model_ref,
    supports_bedrock_native_max_effort,
    resolve_bedrock_claude_thinking_profile,
    resolve_bedrock_native_thinking_level_map,
)

_PROVIDER_ID = "amazon-bedrock"
_BEDROCK_REGION_RE = re.compile(r"bedrock-runtime\.([a-z0-9-]+)\.amazonaws\.")

_CONTEXT_OVERFLOW_PATTERNS = [
    re.compile(r"ValidationException.*(?:input is too long|max input token|input token.*exceed)", re.IGNORECASE),
    re.compile(r"ValidationException.*(?:exceeds? the (?:maximum|max) (?:number of )?(?:input )?tokens)", re.IGNORECASE),
    re.compile(r"ModelStreamErrorException.*(?:Input is too long|too many input tokens)", re.IGNORECASE),
]

_DEPRECATED_TEMPERATURE_VALIDATION_RE = re.compile(
    r"ValidationException[\s\S]*(?:invalid_request_error[\s\S]*)?temperature[\s\S]*deprecated|ValidationException[\s\S]*deprecated[\s\S]*temperature",
    re.IGNORECASE,
)

_SERVICE_TIER_VALUES = ["flex", "priority", "default", "reserved"]

_BEDROCK_APP_INFERENCE_PROFILE_RE = re.compile(
    r"^arn:aws(-cn|-us-gov)?:bedrock:.*:application-inference-profile/",
    re.IGNORECASE,
)


def _normalize_bedrock_resolved_model(ctx: dict[str, Any]) -> dict[str, Any] | None:
    model_id = ctx.get("modelId", "")
    model = ctx.get("model", {})
    thinking_level_map = resolve_bedrock_native_thinking_level_map(model_id, model.get("params"))
    if thinking_level_map is None:
        return None
    reasoning = model.get("reasoning") or resolve_claude_fable5_model_identity({"id": model_id, "params": model.get("params")}) is not None
    current = model.get("thinkingLevelMap")
    if isinstance(current, dict):
        current_efforts = current
    else:
        current_efforts = {}
    if reasoning == model.get("reasoning") and all(
        current_efforts.get(level) == effort for level, effort in thinking_level_map.items()
    ):
        return None
    return {
        **model,
        "reasoning": reasoning,
        "thinkingLevelMap": {**thinking_level_map, **(current if isinstance(current, dict) else {})},
    }


def _is_anthropic_bedrock_model(model_id: str) -> bool:
    normalized = model_id.strip().lower()
    if "anthropic.claude" in normalized or "anthropic/claude" in normalized:
        return True
    if re.match(r"^arn:aws(-cn|-us-gov)?:bedrock:", normalized) and ":application-inference-profile/" in normalized:
        profile_id = normalized.split(":application-inference-profile/")[1] or ""
        return "claude" in profile_id
    return False


def _create_bedrock_no_cache_wrapper(base_stream_fn=None):
    underlying = base_stream_fn or _stream_simple

    def wrapped(model, context, options):
        return underlying(model, context, {**(options or {}), "cacheRetention": "none"})

    return wrapped


def _is_bedrock_service_tier(value: str) -> bool:
    return value in _SERVICE_TIER_VALUES


def _resolve_bedrock_service_tier(
    extra_params: dict[str, Any] | None,
    warn: callable = None,
) -> str | None:
    if extra_params is None:
        return None
    raw = extra_params.get("serviceTier") or extra_params.get("service_tier")
    if not isinstance(raw, str):
        return None
    normalized = raw.strip().lower()
    if _is_bedrock_service_tier(normalized):
        return normalized
    if warn:
        warn(f"ignoring invalid Bedrock service_tier param: {raw}")
    return None


def _create_bedrock_service_tier_wrapper(underlying, service_tier: str):
    def wrapped(model, context, options):
        if model.get("api") != "bedrock-converse-stream":
            return underlying(model, context, options)
        return stream_with_payload_patch(underlying, model, context, options, lambda payload: payload.setdefault("serviceTier", {"type": service_tier}))
    return wrapped


def _create_guardrail_wrap_stream_fn(inner_wrap_stream_fn, guardrail_config: dict[str, Any]):
    def wrap_fn(ctx: dict[str, Any]):
        inner = inner_wrap_stream_fn(ctx)
        if inner is None:
            return inner

        def wrapped(model, context, options):
            def patch_payload(payload):
                gc: dict[str, Any] = {
                    "guardrailIdentifier": guardrail_config.get("guardrailIdentifier", ""),
                    "guardrailVersion": guardrail_config.get("guardrailVersion", ""),
                }
                if guardrail_config.get("streamProcessingMode"):
                    gc["streamProcessingMode"] = guardrail_config["streamProcessingMode"]
                if guardrail_config.get("trace"):
                    gc["trace"] = guardrail_config["trace"]
                payload["guardrailConfig"] = gc

            return stream_with_payload_patch(inner, model, context, options, patch_payload)

        return wrapped

    return wrap_fn


def _shared_runtime_would_inject_cache_points(model_id: str) -> bool:
    return supports_bedrock_prompt_caching(model_id)


def _is_bedrock_app_inference_profile(model_id: str) -> bool:
    return bool(_BEDROCK_APP_INFERENCE_PROFILE_RE.match(model_id))


def _needs_cache_point_injection(model_id: str) -> bool:
    if not _is_bedrock_app_inference_profile(model_id):
        return False
    if _shared_runtime_would_inject_cache_points(model_id):
        return False
    if _is_anthropic_bedrock_model(model_id):
        return True
    return False


def _extract_region_from_arn(arn: str) -> str | None:
    parts = arn.split(":")
    return parts[3] if len(parts) >= 4 and parts[3] else None


def _resolved_model_supports_caching(model_arn: str) -> bool:
    return supports_bedrock_prompt_caching(model_arn)


_APP_PROFILE_TRAITS_CACHE: dict[str, dict[str, Any]] = {}


async def _create_bedrock_control_plane(region: str | None):
    await refresh_aws_shared_config_cache_for_bedrock()
    try:
        from bedrock import BedrockClient, GetInferenceProfileCommand
        client = BedrockClient({"region": region} if region else {})

        async def get_inference_profile(input_data: dict[str, Any]) -> dict[str, Any]:
            resp = client.send(GetInferenceProfileCommand(input_data))
            return resp

        return {"getInferenceProfile": get_inference_profile}
    except ImportError:
        raise ValueError("bedrock package is required for Bedrock control plane operations")


async def _resolve_app_profile_traits(
    model_id: str,
    fallback_region: str | None,
) -> dict[str, Any]:
    cached = _APP_PROFILE_TRAITS_CACHE.get(model_id)
    if cached is not None:
        return cached
    try:
        region = _extract_region_from_arn(model_id) or fallback_region
        control_plane = await _create_bedrock_control_plane(region)
        resp = await control_plane["getInferenceProfile"]({"inferenceProfileIdentifier": model_id})
        models = resp.get("models", []) or []
        model_arns = [m.get("modelArn", "") for m in models]
        traits = {
            "cacheEligible": len(models) > 0 and all(_resolved_model_supports_caching(arn) for arn in model_arns),
            "omitTemperature": any(is_opus47_or_newer_bedrock_model_ref(arn) for arn in model_arns),
        }
        _APP_PROFILE_TRAITS_CACHE[model_id] = traits
        return traits
    except Exception:
        return {
            "cacheEligible": _is_anthropic_bedrock_model(model_id),
            "omitTemperature": is_opus47_or_newer_bedrock_model_ref(model_id),
        }


def _has_cache_point(blocks: list[dict[str, Any]] | None) -> bool:
    if not blocks:
        return False
    return any(b.get("cachePoint") is not None for b in blocks)


def _make_cache_point(cache_retention: str | None) -> dict[str, Any]:
    point: dict[str, Any] = {"cachePoint": {"type": "default"}}
    if cache_retention == "long":
        point["cachePoint"]["ttl"] = "1h"
    return point


def _inject_bedrock_cache_points(payload: dict[str, Any], cache_retention: str | None) -> None:
    if not cache_retention or cache_retention == "none":
        return
    point = _make_cache_point(cache_retention)

    system = payload.get("system")
    if isinstance(system, list) and len(system) > 0 and not _has_cache_point(system):
        system.append(point)

    messages = payload.get("messages")
    if isinstance(messages, list) and len(messages) > 0:
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                if not _has_cache_point(msg["content"]):
                    msg["content"].append(point)
                break


def _patch_max_thinking_effort(payload: dict[str, Any]) -> None:
    fields_value = payload.get("additionalModelRequestFields")
    fields = fields_value if isinstance(fields_value, dict) else {}
    output_config_value = fields.get("output_config")
    output_config = output_config_value if isinstance(output_config_value, dict) else {}
    output_config["effort"] = "max"
    fields["output_config"] = output_config
    payload["additionalModelRequestFields"] = fields


def _omit_unsupported_claude_payload_temperature(payload: dict[str, Any]) -> None:
    inference_config = payload.get("inferenceConfig")
    if not isinstance(inference_config, dict):
        return
    if "temperature" in inference_config:
        del inference_config["temperature"]


def _omit_unsupported_claude_temperature(model_ref: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    canonical_model_id = resolve_claude_model_identity(model_ref)
    omits_temperature = (
        is_opus47_or_newer_bedrock_model_ref(model_ref.get("id", ""))
        or is_opus47_or_newer_bedrock_model_ref(canonical_model_id)
        or resolve_claude_fable5_model_identity(model_ref) is not None
    )
    if not omits_temperature or "temperature" not in options:
        return options
    next_options = {k: v for k, v in options.items() if k != "temperature"}
    return next_options


def _with_aws_credential_refresh_on_payload(options: dict[str, Any]) -> dict[str, Any]:
    original_on_payload = options.get("onPayload")

    async def on_payload(payload, payload_model):
        await refresh_aws_shared_config_cache_for_bedrock()
        if callable(original_on_payload):
            return await original_on_payload(payload, payload_model)
        return None

    return {**options, "onPayload": on_payload}


def _create_aws_credential_refresh_stream_wrapper(stream_fn):
    if stream_fn is None:
        return None

    def wrapped(model, context, options):
        return stream_fn(model, context, _with_aws_credential_refresh_on_payload(options or {}))

    return wrapped


def _extract_region_from_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    match = _BEDROCK_REGION_RE.search(base_url)
    return match.group(1) if match else None


def _resolve_bedrock_region(config: dict[str, Any] | None) -> str | None:
    if config is None:
        return None
    models = config.get("models")
    if not isinstance(models, dict):
        return None
    providers = models.get("providers")
    if not isinstance(providers, dict):
        return None
    exact = providers.get(_PROVIDER_ID)
    if isinstance(exact, dict):
        base_url = exact.get("baseUrl")
        if base_url:
            region = _extract_region_from_base_url(base_url)
            if region:
                return region
    for key, value in providers.items():
        if key == _PROVIDER_ID:
            continue
        if normalize_provider_id(key) == _PROVIDER_ID and isinstance(value, dict):
            base_url = value.get("baseUrl")
            if base_url:
                region = _extract_region_from_base_url(base_url)
                if region:
                    return region
    return None


def _normalize_bedrock_resolved_model_fn(ctx: dict[str, Any]) -> dict[str, Any] | None:
    model_id = ctx.get("modelId", "")
    model = ctx.get("model", {})
    thinking_level_map = resolve_bedrock_native_thinking_level_map(model_id, model.get("params"))
    if thinking_level_map is None:
        return None
    reasoning = model.get("reasoning") or resolve_claude_fable5_model_identity({"id": model_id, "params": model.get("params")}) is not None
    current = model.get("thinkingLevelMap", {})
    if isinstance(current, dict) and all(
        current.get(level) == effort for level, effort in thinking_level_map.items()
    ):
        return None
    return {
        **model,
        "reasoning": reasoning,
        "thinkingLevelMap": {**thinking_level_map, **(current if isinstance(current, dict) else {})},
    }


def register_amazon_bedrock_plugin(api: OpenClawPluginApi) -> None:
    startup_plugin_config = api.plugin_config if is_record(api.plugin_config) else {}

    register_api_provider(
        {
            "api": "bedrock-converse-stream",
            "stream": stream_bedrock,
            "stream_simple": stream_simple_bedrock,
        },
        f"plugin:{_PROVIDER_ID}",
    )

    def resolve_current_plugin_config(config: dict[str, Any] | None) -> dict[str, Any] | None:
        from openclaw.plugin_sdk.plugin_config_runtime import resolve_plugin_config_object
        runtime_plugin_config = resolve_plugin_config_object(config, _PROVIDER_ID)
        if runtime_plugin_config is not None:
            return runtime_plugin_config
        return startup_plugin_config if config is None else None

    api.register_memory_embedding_provider(bedrock_memory_embedding_provider_adapter)

    def base_wrap_stream_fn(ctx: dict[str, Any]):
        model_id = ctx.get("modelId", "")
        model = ctx.get("model", {})
        stream_fn = ctx.get("streamFn")
        model_ref = {"id": model_id, "params": model.get("params")}

        if _is_anthropic_bedrock_model(model_id) or resolve_claude_model_identity(model_ref).startswith("claude-"):
            return stream_fn
        if _is_bedrock_app_inference_profile(model_id):
            return stream_fn
        return _create_bedrock_no_cache_wrapper(stream_fn)

    def classify_failover_reason(ctx: dict[str, Any]) -> str | None:
        error_message = str(ctx.get("errorMessage", ""))
        if re.search(r"ThrottlingException|Too many concurrent requests", error_message, re.IGNORECASE):
            return "rate_limit"
        if re.search(r"ModelNotReadyException", error_message, re.IGNORECASE):
            return "overloaded"
        if _DEPRECATED_TEMPERATURE_VALIDATION_RE.search(error_message):
            return "format"
        return None

    api.register_provider(
        {
            "id": _PROVIDER_ID,
            "label": "Amazon Bedrock",
            "docsPath": "/providers/models",
            "auth": [],
            "catalog": {
                "order": "simple",
                "run": lambda ctx: _catalog_run(ctx, resolve_current_plugin_config),
            },
            "resolveConfigApiKey": lambda ctx: resolve_bedrock_config_api_key(ctx.get("env")),
            "normalizeResolvedModel": _normalize_bedrock_resolved_model_fn,
            **ANTHROPIC_BY_MODEL_REPLAY_HOOKS,
            "wrapStreamFn": lambda ctx: _wrap_stream_fn(ctx, api, resolve_current_plugin_config, base_wrap_stream_fn),
            "matchesContextOverflowError": lambda ctx: any(
                pattern.search(str(ctx.get("errorMessage", ""))) for pattern in _CONTEXT_OVERFLOW_PATTERNS
            ),
            "classifyFailoverReason": classify_failover_reason,
            "resolveThinkingProfile": lambda ctx: resolve_bedrock_claude_thinking_profile(
                ctx.get("modelId", ""),
                ctx.get("params"),
            ),
        }
    )


async def _catalog_run(ctx: dict[str, Any], resolve_current_plugin_config) -> dict[str, Any] | None:
    from openclaw_extensions.amazon_bedrock.discovery import resolve_implicit_bedrock_provider
    current_plugin_config = resolve_current_plugin_config(ctx.get("config"))
    implicit = await resolve_implicit_bedrock_provider({
        "pluginConfig": current_plugin_config,
        "env": ctx.get("env"),
    })
    if not implicit:
        return None
    config = ctx.get("config", {})
    models = config.get("models", {}) if isinstance(config, dict) else {}
    providers = models.get("providers", {}) if isinstance(models, dict) else {}
    existing = providers.get(_PROVIDER_ID) if isinstance(providers, dict) else None
    return {
        "provider": merge_implicit_bedrock_provider({
            "existing": existing,
            "implicit": implicit,
        }),
    }


def _wrap_stream_fn(
    ctx: dict[str, Any],
    api: OpenClawPluginApi,
    resolve_current_plugin_config,
    base_wrap_stream_fn,
):
    model_id = ctx.get("modelId", "")
    model = ctx.get("model", {})
    stream_fn = ctx.get("streamFn")
    thinking_level = ctx.get("thinkingLevel")
    extra_params = ctx.get("extraParams")

    def get_current_plugin_config():
        return resolve_current_plugin_config(ctx.get("config"))

    current_plugin_config = get_current_plugin_config()
    current_guardrail = current_plugin_config.get("guardrail") if isinstance(current_plugin_config, dict) else None
    model_ref = {"id": model_id, "params": model.get("params")}
    fable5 = resolve_claude_fable5_model_identity(model_ref) is not None
    canonical_model_id = resolve_claude_model_identity(model_ref)
    opus47_or_newer = (
        is_opus47_or_newer_bedrock_model_ref(model_id)
        or is_opus47_or_newer_bedrock_model_ref(canonical_model_id)
    )
    supports_native_max = supports_bedrock_native_max_effort(model_id, model.get("params"))

    wrapped = None
    if current_guardrail and current_guardrail.get("guardrailIdentifier") and current_guardrail.get("guardrailVersion"):
        wrapped = _create_guardrail_wrap_stream_fn(base_wrap_stream_fn, current_guardrail)({
            "modelId": model_id,
            "model": model,
            "streamFn": stream_fn,
        })
    else:
        wrapped = base_wrap_stream_fn({"modelId": model_id, "model": model, "streamFn": stream_fn})

    service_tier = _resolve_bedrock_service_tier(extra_params, lambda msg: api.logger.warn(msg))
    if service_tier and wrapped:
        if fable5 and service_tier != "default":
            api.logger.warn(f"ignoring unsupported Fable 5 Bedrock service tier: {service_tier}")
        else:
            wrapped = _create_bedrock_service_tier_wrapper(wrapped, service_tier)

    config = ctx.get("config")
    region = (
        _resolve_bedrock_region(config)
        or _extract_region_from_base_url(model.get("baseUrl"))
        or (current_plugin_config.get("discovery", {}) or {}).get("region")
        if isinstance(current_plugin_config, dict)
        else None
    )

    may_need_cache_injection = (
        _is_bedrock_app_inference_profile(model_id)
        and not _shared_runtime_would_inject_cache_points(model_id)
    )
    should_omit_temperature = (
        opus47_or_newer or fable5 or is_latest_adaptive_bedrock_model_ref(model_id, model.get("params"))
    )
    should_patch_max_thinking = supports_native_max and thinking_level == "max"
    should_patch_payload = should_omit_temperature or should_patch_max_thinking

    heuristic_match = _needs_cache_point_injection(model_id)

    if not region and not may_need_cache_injection and not should_omit_temperature and not should_patch_max_thinking:
        return _create_aws_credential_refresh_stream_wrapper(wrapped)

    underlying = wrapped or stream_fn
    if underlying is None:
        return wrapped

    def final_stream_fn(stream_model, context, options):
        merged = _omit_unsupported_claude_temperature(
            model_ref,
            {**(options or {}), **({"region": region} if region else {})},
        )

        original_on_payload = merged.get("onPayload")

        if not may_need_cache_injection:
            result_options = _with_aws_credential_refresh_on_payload(merged)
            if should_patch_payload:
                async def patched_on_payload(payload, payload_model):
                    if isinstance(payload, dict):
                        if should_patch_max_thinking:
                            _patch_max_thinking_effort(payload)
                        if should_omit_temperature:
                            _omit_unsupported_claude_payload_temperature(payload)
                    if callable(original_on_payload):
                        return await original_on_payload(payload, payload_model)
                    return None
                result_options["onPayload"] = patched_on_payload
            return underlying(stream_model, context, result_options)

        cache_retention_value = merged.get("cacheRetention", "short")
        if isinstance(cache_retention_value, str):
            cache_retention = cache_retention_value
        else:
            cache_retention = "short"

        if heuristic_match:
            may_need_temperature_trait = "temperature" in merged
            result_options = _with_aws_credential_refresh_on_payload(merged)

            async def heuristic_on_payload(payload, payload_model):
                if isinstance(payload, dict):
                    _inject_bedrock_cache_points(payload, cache_retention)
                    if should_patch_max_thinking:
                        _patch_max_thinking_effort(payload)
                    if should_omit_temperature:
                        _omit_unsupported_claude_payload_temperature(payload)
                    elif may_need_temperature_trait:
                        traits = await _resolve_app_profile_traits(model_id, region)
                        if traits.get("omitTemperature"):
                            _omit_unsupported_claude_payload_temperature(payload)
                if callable(original_on_payload):
                    return await original_on_payload(payload, payload_model)
                return None
            result_options["onPayload"] = heuristic_on_payload
            return underlying(stream_model, context, result_options)

        result_options = _with_aws_credential_refresh_on_payload(merged)

        async def async_on_payload(payload, payload_model):
            traits = await _resolve_app_profile_traits(model_id, region)
            if isinstance(payload, dict):
                if traits.get("cacheEligible"):
                    _inject_bedrock_cache_points(payload, cache_retention)
                if should_patch_max_thinking:
                    _patch_max_thinking_effort(payload)
                if traits.get("omitTemperature"):
                    _omit_unsupported_claude_payload_temperature(payload)
            if callable(original_on_payload):
                return await original_on_payload(payload, payload_model)
            return None
        result_options["onPayload"] = async_on_payload
        return underlying(stream_model, context, result_options)

    return final_stream_fn


__all__ = ["register_amazon_bedrock_plugin"]