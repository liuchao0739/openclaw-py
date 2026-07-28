from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from openclaw.plugin_sdk.provider_stream_shared import (
    create_anthropic_thinking_prefill_payload_wrapper,
    stream_with_payload_patch,
)

_log = logging.getLogger("anthropic-stream")

_ANTHROPIC_CONTEXT_1M_BETA_LEGACY = "context-1m-2025-08-07"
_ANTHROPIC_GA_1M_MODEL_PREFIXES = [
    "claude-opus-4-8",
    "claude-opus-4.8",
    "claude-opus-4-6",
    "claude-opus-4.6",
    "claude-opus-4-7",
    "claude-opus-4.7",
    "claude-sonnet-4-6",
    "claude-sonnet-4.6",
]
_OPENCLAW_DEFAULT_ANTHROPIC_BETAS = [
    "fine-grained-tool-streaming-2025-05-14",
    "interleaved-thinking-2025-05-14",
]
_OPENCLAW_OAUTH_ANTHROPIC_BETAS = [
    "claude-code-20250219",
    "oauth-2025-04-20",
    *_OPENCLAW_DEFAULT_ANTHROPIC_BETAS,
]


def _is_anthropic_1m_model(model_id: str) -> bool:
    from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty

    normalized = normalize_lowercase_string_or_empty(model_id)
    return any(normalized.startswith(prefix) for prefix in _ANTHROPIC_GA_1M_MODEL_PREFIXES)


def _parse_header_list(value: Any) -> list[str]:
    if not isinstance(value, str):
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _merge_anthropic_beta_header(
    headers: dict[str, str] | None,
    betas: list[str],
) -> dict[str, str]:
    merged = dict(headers) if headers else {}
    existing_key = next(
        (
            k
            for k in merged
            if k.lower() == "anthropic-beta"
        ),
        None,
    )
    existing = _parse_header_list(merged.get(existing_key, "")) if existing_key else []
    values = list(dict.fromkeys([*existing, *betas]))
    key = existing_key or "anthropic-beta"
    merged[key] = ",".join(values)
    return merged


def _is_anthropic_oauth_api_key(api_key: Any) -> bool:
    return isinstance(api_key, str) and "sk-ant-oat" in api_key


def _resolve_anthropic_fast_service_tier(enabled: bool) -> str:
    return "auto" if enabled else "standard_only"


def _normalize_anthropic_service_tier(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in ("auto", "standard_only"):
        return normalized
    return None


def _has_configured_anthropic_beta(
    extra_params: dict[str, Any] | None,
) -> bool:
    if not isinstance(extra_params, dict):
        return False
    configured = extra_params.get("anthropicBeta")
    if isinstance(configured, str):
        return bool(configured.strip())
    if not isinstance(configured, list):
        return False
    return any(
        isinstance(beta, str) and beta.strip()
        for beta in configured
    )


def resolve_anthropic_betas(
    extra_params: dict[str, Any] | None,
    _model_id: str,
) -> list[str] | None:
    betas: set[str] = set()
    if isinstance(extra_params, dict):
        configured = extra_params.get("anthropicBeta")
        if isinstance(configured, str) and configured.strip():
            for beta in _parse_header_list(configured):
                betas.add(beta)
        elif isinstance(configured, list):
            for beta in configured:
                if isinstance(beta, str) and beta.strip():
                    for beta_value in _parse_header_list(beta):
                        betas.add(beta_value)

    betas.discard(_ANTHROPIC_CONTEXT_1M_BETA_LEGACY)
    return list(betas) if betas else None


def create_anthropic_beta_headers_wrapper(
    base_stream_fn: Callable[..., Any] | None,
    betas: list[str],
) -> Callable[..., Any]:
    underlying = base_stream_fn
    if underlying is None:
        from openclaw.plugin_sdk.llm import stream_simple
        underlying = stream_simple

    def wrapped(model: Any, context: Any, options: dict[str, Any] | None = None) -> Any:
        opts = dict(options or {})
        api_key = opts.get("apiKey") or (opts.get("headers") or {}).get("x-api-key")
        is_oauth = _is_anthropic_oauth_api_key(api_key) if api_key else False
        effective_betas = [b for b in betas if b != _ANTHROPIC_CONTEXT_1M_BETA_LEGACY]
        openclaw_betas = (
            _OPENCLAW_OAUTH_ANTHROPIC_BETAS
            if is_oauth
            else _OPENCLAW_DEFAULT_ANTHROPIC_BETAS
        )
        all_betas = list(dict.fromkeys([*openclaw_betas, *effective_betas]))
        opts["headers"] = _merge_anthropic_beta_header(
            opts.get("headers"), all_betas
        )
        return underlying(model, context, opts)

    return wrapped


def create_anthropic_fast_mode_wrapper(
    base_stream_fn: Callable[..., Any] | None,
    enabled: Any,
) -> Callable[..., Any]:
    underlying = base_stream_fn
    if underlying is None:
        from openclaw.plugin_sdk.llm import stream_simple
        underlying = stream_simple

    def wrapped(model: Any, context: Any, options: dict[str, Any] | None = None) -> Any:
        resolved = enabled() if callable(enabled) else enabled
        if resolved is None:
            return underlying(model, context, options)
        service_tier_wrapper = create_anthropic_service_tier_wrapper(
            underlying, _resolve_anthropic_fast_service_tier(resolved)
        )
        return service_tier_wrapper(model, context, options)

    return wrapped


def create_anthropic_service_tier_wrapper(
    base_stream_fn: Callable[..., Any] | None,
    service_tier: str,
) -> Callable[..., Any]:
    underlying = base_stream_fn
    if underlying is None:
        from openclaw.plugin_sdk.llm import stream_simple
        underlying = stream_simple

    def wrapped(model: Any, context: Any, options: dict[str, Any] | None = None) -> Any:
        opts = dict(options or {})
        api_key = opts.get("apiKey") or (opts.get("headers") or {}).get("x-api-key")
        if _is_anthropic_oauth_api_key(api_key) if api_key else False:
            return underlying(model, context, options)

        try:
            from openclaw.plugin_sdk.provider_stream_shared import (
                apply_anthropic_payload_policy_to_params,
                resolve_anthropic_payload_policy,
            )
            from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty

            provider = model.get("provider") if isinstance(model, dict) else ""
            api = model.get("api") if isinstance(model, dict) else ""
            base_url = model.get("baseUrl") if isinstance(model, dict) else ""
            payload_policy = resolve_anthropic_payload_policy({
                "provider": normalize_lowercase_string_or_empty(provider),
                "api": normalize_lowercase_string_or_empty(api),
                "baseUrl": normalize_lowercase_string_or_empty(base_url),
                "serviceTier": service_tier,
            })
            if not payload_policy.get("allowsServiceTier"):
                return underlying(model, context, options)

            def patch(payload_obj: dict[str, Any]) -> None:
                apply_anthropic_payload_policy_to_params(payload_obj, payload_policy)

            return stream_with_payload_patch(underlying, model, context, options, patch)
        except ImportError:
            return underlying(model, context, options)

    return wrapped


def create_anthropic_thinking_prefill_wrapper(
    base_stream_fn: Callable[..., Any] | None,
) -> Callable[..., Any]:
    def on_stripped(stripped: int) -> None:
        suffix = "" if stripped == 1 else "s"
        _log.warning(
            "removed %s trailing assistant prefill message%s because Anthropic extended "
            "thinking requires conversations to end with a user turn",
            stripped,
            suffix,
        )

    return create_anthropic_thinking_prefill_payload_wrapper(base_stream_fn, on_stripped)


def resolve_anthropic_fast_mode(
    extra_params: dict[str, Any] | None,
) -> bool | None:
    from openclaw.packages.normalization_core import normalize_optional_string

    if not isinstance(extra_params, dict):
        return None
    raw = extra_params.get("fastMode")
    if raw is None:
        raw = extra_params.get("fast_mode")
    if callable(raw):
        from openclaw.packages.normalization_core import normalize_fast_mode
        fast_mode = normalize_fast_mode(raw())
    else:
        from openclaw.packages.normalization_core import normalize_fast_mode
        fast_mode = normalize_fast_mode(raw)
    if fast_mode == "auto":
        return None
    return fast_mode


def resolve_anthropic_service_tier(
    extra_params: dict[str, Any] | None,
) -> str | None:
    if not isinstance(extra_params, dict):
        return None
    raw = extra_params.get("serviceTier")
    if raw is None:
        raw = extra_params.get("service_tier")
    normalized = _normalize_anthropic_service_tier(raw)
    if raw is not None and normalized is None:
        raw_summary = raw if isinstance(raw, str) else type(raw).__name__
        _log.warning("ignoring invalid Anthropic service tier param: %s", raw_summary)
    return normalized


def wrap_anthropic_provider_stream(
    ctx: dict[str, Any],
) -> Callable[..., Any] | None:
    extra_params = ctx.get("extraParams") if isinstance(ctx, dict) else None
    model_id = ctx.get("modelId", "") if isinstance(ctx, dict) else ""
    anthropic_betas = resolve_anthropic_betas(extra_params, model_id)
    needs_anthropic_beta_wrapper = (
        anthropic_betas is not None
        or _has_configured_anthropic_beta(extra_params)
        or (
            isinstance(extra_params, dict)
            and extra_params.get("context1m") is True
            and _is_anthropic_1m_model(model_id)
        )
    )
    service_tier = resolve_anthropic_service_tier(extra_params)
    has_fast_mode_param = (
        isinstance(extra_params, dict)
        and ("fastMode" in extra_params or "fast_mode" in extra_params)
    )

    wrappers: list[Callable[..., Any] | None] = []

    stream_fn = ctx.get("streamFn") if isinstance(ctx, dict) else None

    if needs_anthropic_beta_wrapper:
        wrappers.append(
            lambda fn: create_anthropic_beta_headers_wrapper(fn, anthropic_betas or [])
        )
    else:
        wrappers.append(None)

    if service_tier:
        wrappers.append(
            lambda fn: create_anthropic_service_tier_wrapper(fn, service_tier)
        )
    else:
        wrappers.append(None)

    if has_fast_mode_param:
        wrappers.append(
            lambda fn: create_anthropic_fast_mode_wrapper(
                fn,
                lambda: resolve_anthropic_fast_mode(extra_params),
            )
        )
    else:
        wrappers.append(None)

    wrappers.append(create_anthropic_thinking_prefill_wrapper)

    result = stream_fn
    for wrapper in wrappers:
        if wrapper is not None:
            result = wrapper(result)

    return result


class _TestingExports:
    log = _log


testing = _TestingExports()
__testing__ = testing