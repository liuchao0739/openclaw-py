"""Anthropic Vertex stream runtime."""

from __future__ import annotations

import importlib
import math
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse, urlunparse

from openclaw_extensions.anthropic_vertex.claude_contracts import (
    clamp_thinking_level,
    resolve_claude_fable5_model_identity,
    resolve_claude_model_identity,
    supports_claude_adaptive_thinking,
    supports_claude_native_max_effort,
    supports_claude_native_xhigh_effort,
)
from openclaw_extensions.anthropic_vertex.region import (
    resolve_anthropic_vertex_client_region,
    resolve_anthropic_vertex_project_id,
)
from openclaw_packages.llm_runtime.stream import stream as default_stream

AnthropicVertexEffort = str
AnthropicVertexAdaptiveEffort = str


def _default_anthropic_vertex_ctor() -> Any:
    vertex_module = importlib.import_module("anthropic")
    return vertex_module.AnthropicVertex


def _is_claude_opus47_or_newer_model(model_id: str) -> bool:
    return supports_claude_native_xhigh_effort({"id": model_id})


def _is_claude_fable5_model(model_id: str) -> bool:
    return resolve_claude_fable5_model_identity({"id": model_id}) is not None


def _is_claude_mythos5_model(model_id: str) -> bool:
    return bool(
        re.search(
            r"(?:^|-)claude-mythos-5(?=$|[^a-z0-9])",
            resolve_claude_model_identity({"id": model_id}),
        )
    )


def _supports_adaptive_thinking(model_id: str) -> bool:
    return supports_claude_adaptive_thinking({"id": model_id}) or _is_claude_mythos5_model(
        model_id
    )


def _map_anthropic_adaptive_effort(
    reasoning: str,
    model: dict[str, Any],
    model_id: str,
) -> AnthropicVertexAdaptiveEffort:
    params = model.get("params")
    clamp_model = (
        {**model, "reasoning": True}
        if isinstance(params, dict) and isinstance(params.get("canonicalModelId"), str)
        else model
    )
    resolved_reasoning = clamp_thinking_level(clamp_model, reasoning)
    thinking_level_map = model.get("thinkingLevelMap")
    if isinstance(thinking_level_map, dict) and isinstance(thinking_level_map.get(resolved_reasoning), str):
        return thinking_level_map[resolved_reasoning]

    effort_map: dict[str, AnthropicVertexAdaptiveEffort] = {
        "off": "low",
        "minimal": "low",
        "low": "low",
        "medium": "medium",
        "high": "high",
        "xhigh": (
            "xhigh"
            if _is_claude_fable5_model(model_id)
            or _is_claude_opus47_or_newer_model(model_id)
            or _is_claude_mythos5_model(model_id)
            else "high"
        ),
        "max": (
            "max"
            if supports_claude_native_max_effort({"id": model_id}) or _is_claude_mythos5_model(model_id)
            else "high"
        ),
    }
    return effort_map.get(resolved_reasoning, "high")


def _resolve_anthropic_vertex_max_tokens(params: dict[str, Any]) -> int | None:
    model_max = params.get("modelMaxTokens")
    requested = params.get("requestedMaxTokens")
    model_max_tokens = (
        math.floor(model_max)
        if isinstance(model_max, (int, float))
        and math.isfinite(model_max)
        and model_max > 0
        else None
    )
    requested_max_tokens = (
        math.floor(requested)
        if isinstance(requested, (int, float))
        and math.isfinite(requested)
        and requested > 0
        else None
    )
    if model_max_tokens is not None and requested_max_tokens is not None:
        return min(requested_max_tokens, model_max_tokens)
    return requested_max_tokens if requested_max_tokens is not None else model_max_tokens


def create_anthropic_vertex_stream_fn(
    project_id: str | None,
    region: str,
    base_url: str | None = None,
    deps: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    """Create a StreamFn that routes through the shared anthropic-messages transport."""
    resolved_deps = deps or {}
    anthropic_vertex_ctor = resolved_deps.get("AnthropicVertex") or _default_anthropic_vertex_ctor()
    stream_anthropic = resolved_deps.get("streamAnthropic") or default_stream

    client_options: dict[str, Any] = {"region": region}
    if base_url:
        client_options["baseURL"] = base_url
    if project_id:
        client_options["projectId"] = project_id
    client = anthropic_vertex_ctor(client_options)

    def stream_fn(model: Any, context: Any, options: dict[str, Any] | None = None) -> Any:
        resolved_options = options or {}
        transport_model = model if isinstance(model, dict) else {}
        max_tokens = _resolve_anthropic_vertex_max_tokens(
            {
                "modelMaxTokens": transport_model.get("maxTokens") or transport_model.get(
                    "max_tokens"
                ),
                "requestedMaxTokens": resolved_options.get("maxTokens")
                or resolved_options.get("max_tokens"),
            }
        )
        contract_model_id = resolve_claude_model_identity(transport_model)
        fable5 = _is_claude_fable5_model(contract_model_id)
        mandatory_adaptive_thinking = fable5 or _is_claude_mythos5_model(contract_model_id)
        reasoning = resolved_options.get("reasoning")
        if reasoning is None and mandatory_adaptive_thinking:
            reasoning = "high"
        adaptive_thinking = mandatory_adaptive_thinking or bool(
            reasoning and _supports_adaptive_thinking(contract_model_id)
        )
        temperature = (
            None
            if adaptive_thinking
            or _is_claude_opus47_or_newer_model(contract_model_id)
            or _is_claude_mythos5_model(contract_model_id)
            else resolved_options.get("temperature")
        )

        opts: dict[str, Any] = {
            "client": client,
            "signal": resolved_options.get("signal"),
            "cacheRetention": resolved_options.get("cacheRetention")
            or resolved_options.get("cache_retention"),
            "sessionId": resolved_options.get("sessionId") or resolved_options.get("session_id"),
            "headers": resolved_options.get("headers"),
            "onPayload": resolved_options.get("onPayload") or resolved_options.get("on_payload"),
            "maxRetryDelayMs": resolved_options.get("maxRetryDelayMs")
            or resolved_options.get("max_retry_delay_ms"),
            "metadata": resolved_options.get("metadata"),
        }
        if temperature is not None:
            opts["temperature"] = temperature
        if max_tokens is not None:
            opts["maxTokens"] = max_tokens

        if reasoning:
            if _supports_adaptive_thinking(contract_model_id):
                opts["thinkingEnabled"] = True
                opts["effort"] = _map_anthropic_adaptive_effort(
                    str(reasoning),
                    transport_model,
                    contract_model_id,
                )
            else:
                opts["thinkingEnabled"] = True
                budgets = resolved_options.get("thinkingBudgets") or resolved_options.get(
                    "thinking_budgets"
                )
                budget = (
                    budgets.get(reasoning)
                    if isinstance(budgets, dict) and reasoning in budgets
                    else None
                )
                opts["thinkingBudgetTokens"] = budget if budget is not None else 10000
        elif fable5:
            opts["thinkingEnabled"] = True
            opts["effort"] = "high"
        else:
            opts["thinkingEnabled"] = False

        return stream_anthropic(model, context, opts)

    return stream_fn


def _resolve_anthropic_vertex_sdk_base_url(base_url: str | None) -> str | None:
    trimmed = base_url.strip() if isinstance(base_url, str) else ""
    if not trimmed:
        return None
    try:
        parsed = urlparse(trimmed)
        normalized_path = re.sub(r"/+$", "", parsed.path or "")
        if not normalized_path:
            return urlunparse(
                (parsed.scheme, parsed.netloc, "/v1", parsed.params, parsed.query, parsed.fragment)
            ).rstrip("/")
        if not normalized_path.endswith("/v1"):
            return urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    f"{normalized_path}/v1",
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            ).rstrip("/")
        return trimmed
    except ValueError:
        return trimmed


def create_anthropic_vertex_stream_fn_for_model(
    model: dict[str, Any],
    env: dict[str, str] | None = None,
    deps: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    """Create an Anthropic Vertex stream function from model metadata and env."""
    base_url = model.get("baseUrl") or model.get("base_url")
    return create_anthropic_vertex_stream_fn(
        resolve_anthropic_vertex_project_id(env),
        resolve_anthropic_vertex_client_region({"baseUrl": base_url, "env": env}),
        _resolve_anthropic_vertex_sdk_base_url(base_url if isinstance(base_url, str) else None),
        deps,
    )
