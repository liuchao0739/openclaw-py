"""Anthropic Messages stream adapter for Bedrock Mantle."""

from __future__ import annotations

import importlib
import re
from collections.abc import Callable
from typing import Any

from openclaw_packages.llm_runtime.stream import stream as default_stream

MANTLE_ANTHROPIC_BETA = "fine-grained-tool-streaming-2025-05-14"


def resolve_mantle_anthropic_base_url(base_url: str) -> str:
    """Resolve the Anthropic-compatible Mantle base URL from a provider base URL."""
    trimmed = re.sub(r"/+$", "", base_url)
    if trimmed.endswith("/anthropic"):
        return trimmed
    if trimmed.endswith("/v1"):
        return f"{trimmed[:-3]}/anthropic"
    return f"{trimmed}/anthropic"


def _model_field(model: Any, *keys: str, default: Any = None) -> Any:
    if isinstance(model, dict):
        for key in keys:
            if key in model:
                return model[key]
        return default
    for key in keys:
        value = getattr(model, key, None)
        if value is not None:
            return value
        snake_key = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()
        value = getattr(model, snake_key, None)
        if value is not None:
            return value
    return default


def _requires_default_sampling(model_id: str) -> bool:
    return "claude-opus-4-7" in model_id


def _normalize_mythos_token(value: str) -> str:
    return re.sub(r"[\s_.:]+", "-", value.strip().lower())


def _is_claude_mythos_preview_model(model: Any) -> bool:
    candidates = [
        _model_field(model, "id"),
        _model_field(model, "name"),
        _model_field(model, "params", default={}).get("canonicalModelId")
        if isinstance(_model_field(model, "params", default={}), dict)
        else None,
    ]
    pattern = re.compile(r"(?:^|-)claude-mythos-preview(?=$|[^a-z0-9])")
    for candidate in candidates:
        if isinstance(candidate, str) and pattern.search(_normalize_mythos_token(candidate)):
            return True
    return False


def _resolve_mantle_reasoning(model: Any, options: dict[str, Any] | None) -> str | None:
    model_id = str(_model_field(model, "id", default=""))
    if _requires_default_sampling(model_id):
        return None

    reasoning = options.get("reasoning") if options else None
    if reasoning is None and _is_claude_mythos_preview_model(model):
        reasoning = "high"
    if not _is_claude_mythos_preview_model(model):
        return reasoning
    if reasoning == "minimal":
        return "low"
    if reasoning in {"xhigh", "max"}:
        return "high"
    return reasoning


def _merge_headers(*header_sources: dict[str, str] | None) -> dict[str, str]:
    merged: dict[str, str] = {}
    for headers in header_sources:
        if headers:
            merged.update(headers)
    return merged


def _build_mantle_anthropic_base_options(
    model: Any,
    options: dict[str, Any] | None,
    api_key: str,
) -> dict[str, Any]:
    model_max_tokens = int(_model_field(model, "maxTokens", "max_tokens", default=0) or 0)
    requested_max_tokens = options.get("maxTokens") if options else None
    if requested_max_tokens is None and options:
        requested_max_tokens = options.get("max_tokens")
    return {
        "temperature": None
        if _requires_default_sampling(str(_model_field(model, "id", default="")))
        else (options or {}).get("temperature"),
        "maxTokens": requested_max_tokens or min(model_max_tokens, 32_000),
        "signal": (options or {}).get("signal"),
        "apiKey": api_key,
        "cacheRetention": (options or {}).get("cacheRetention")
        or (options or {}).get("cache_retention"),
        "sessionId": (options or {}).get("sessionId") or (options or {}).get("session_id"),
        "onPayload": (options or {}).get("onPayload") or (options or {}).get("on_payload"),
        "maxRetryDelayMs": (options or {}).get("maxRetryDelayMs")
        or (options or {}).get("max_retry_delay_ms"),
        "metadata": (options or {}).get("metadata"),
    }


def _adjust_max_tokens_for_thinking(
    base_max_tokens: int,
    model_max_tokens: int,
    reasoning_level: str,
    custom_budgets: dict[str, int] | None = None,
) -> dict[str, int]:
    default_budgets = {
        "minimal": 1024,
        "low": 2048,
        "medium": 8192,
        "high": 16384,
        "xhigh": 16384,
        "max": 16384,
    }
    budgets = {**default_budgets, **(custom_budgets or {})}
    min_output_tokens = 1024
    thinking_budget = budgets[reasoning_level]
    max_tokens = min(base_max_tokens + thinking_budget, model_max_tokens)
    if max_tokens <= thinking_budget:
        thinking_budget = max(0, max_tokens - min_output_tokens)
    return {"maxTokens": max_tokens, "thinkingBudget": thinking_budget}


def _default_create_client(client_options: dict[str, Any]) -> Any:
    anthropic_module = importlib.import_module("anthropic")
    anthropic_cls = anthropic_module.Anthropic
    return anthropic_cls(
        api_key=client_options.get("apiKey"),
        auth_token=client_options.get("authToken"),
        base_url=client_options.get("baseURL"),
        dangerously_allow_browser=client_options.get("dangerouslyAllowBrowser", False),
        default_headers=client_options.get("defaultHeaders"),
    )


def create_mantle_anthropic_stream_fn(
    deps: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    """Create the Mantle Anthropic Messages stream function."""
    resolved_deps = deps or {}

    def stream_fn(model: Any, context: Any, options: dict[str, Any] | None = None) -> Any:
        resolved_options = options or {}
        api_key = resolved_options.get("apiKey") or resolved_options.get("api_key") or ""
        create_client = resolved_deps.get("createClient") or resolved_deps.get(
            "create_client"
        ) or _default_create_client
        stream_impl = resolved_deps.get("stream") or default_stream

        model_headers = _model_field(model, "headers", default={})
        model_headers = model_headers if isinstance(model_headers, dict) else {}
        option_headers = resolved_options.get("headers")
        option_headers = option_headers if isinstance(option_headers, dict) else {}

        client = create_client(
            {
                "apiKey": None,
                "authToken": api_key,
                "baseURL": resolve_mantle_anthropic_base_url(
                    str(_model_field(model, "baseUrl", "base_url", default=""))
                ),
                "dangerouslyAllowBrowser": True,
                "defaultHeaders": _merge_headers(
                    {
                        "accept": "application/json",
                        "anthropic-dangerous-direct-browser-access": "true",
                        "anthropic-beta": MANTLE_ANTHROPIC_BETA,
                    },
                    model_headers,
                    option_headers,
                ),
            }
        )
        base = _build_mantle_anthropic_base_options(model, resolved_options, api_key)
        reasoning = _resolve_mantle_reasoning(model, resolved_options)
        if not reasoning:
            return stream_impl(
                model,
                context,
                {
                    **base,
                    "client": client,
                    "thinkingEnabled": False,
                },
            )

        adjusted = _adjust_max_tokens_for_thinking(
            int(base.get("maxTokens") or 0),
            int(_model_field(model, "maxTokens", "max_tokens", default=0) or 0),
            reasoning,
            resolved_options.get("thinkingBudgets") or resolved_options.get("thinking_budgets"),
        )
        stream_options: dict[str, Any] = {
            **base,
            "client": client,
            "maxTokens": adjusted["maxTokens"],
            "thinkingEnabled": True,
            "thinkingBudgetTokens": adjusted["thinkingBudget"],
        }
        if _is_claude_mythos_preview_model(model):
            stream_options["effort"] = reasoning
        return stream_impl(model, context, stream_options)

    return stream_fn
