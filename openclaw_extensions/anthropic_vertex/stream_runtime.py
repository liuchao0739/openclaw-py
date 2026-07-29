import math
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

from openclaw.plugin_sdk.llm import clamp_thinking_level, stream as stream_default
from openclaw.plugin_sdk.provider_model_shared import (
    resolve_claude_fable5_model_identity,
    resolve_claude_model_identity,
    supports_claude_adaptive_thinking,
    supports_claude_native_max_effort,
    supports_claude_native_xhigh_effort,
)

from .region import resolve_anthropic_vertex_client_region, resolve_anthropic_vertex_project_id


class AnthropicVertexStreamDeps:
    def __init__(self, anthropic_vertex_cls, stream_anthropic):
        self.AnthropicVertex = anthropic_vertex_cls
        self.streamAnthropic = stream_anthropic


def _default_anthropic_vertex_stream_deps():
    from anthropic_ai_vertex_sdk import AnthropicVertex as AnthropicVertexSdk

    return AnthropicVertexStreamDeps(AnthropicVertexSdk, stream_default)


def _is_claude_opus47_or_newer_model(model_id: str) -> bool:
    return supports_claude_native_xhigh_effort({"id": model_id})


def _is_claude_fable5_model(model_id: str) -> bool:
    return resolve_claude_fable5_model_identity({"id": model_id}) is not None


def _is_claude_mythos5_model(model_id: str) -> bool:
    import re

    identity = resolve_claude_model_identity({"id": model_id})
    return re.search(r"(?:^|-)claude-mythos-5(?=$|[^a-z0-9])", identity) is not None


def _supports_adaptive_thinking(model_id: str) -> bool:
    return supports_claude_adaptive_thinking({"id": model_id}) or _is_claude_mythos5_model(model_id)


def _map_anthropic_adaptive_effort(reasoning, model, model_id: str):
    clamp_model = {**model, "reasoning": True} if isinstance(model.get("params", {}).get("canonicalModelId"), str) else model
    resolved_reasoning = clamp_thinking_level(clamp_model, reasoning)
    thinking_level_map = model.get("thinkingLevelMap") or {}
    mapped = thinking_level_map.get(resolved_reasoning)
    if isinstance(mapped, str):
        return mapped
    effort_map = {
        "off": "low",
        "minimal": "low",
        "low": "low",
        "medium": "medium",
        "high": "high",
        "xhigh": (
            "xhigh"
            if _is_claude_fable5_model(model_id)
            else ("xhigh" if _is_claude_opus47_or_newer_model(model_id) or _is_claude_mythos5_model(model_id) else "high")
        ),
        "max": (
            "max"
            if supports_claude_native_max_effort({"id": model_id}) or _is_claude_mythos5_model(model_id)
            else "high"
        ),
    }
    return effort_map.get(resolved_reasoning, "high")


def _resolve_anthropic_vertex_max_tokens(params: dict) -> Optional[int]:
    model_max_tokens = params.get("modelMaxTokens")
    model_max = (
        math.floor(model_max_tokens)
        if isinstance(model_max_tokens, (int, float))
        and math.isfinite(model_max_tokens)
        and model_max_tokens > 0
        else None
    )
    requested_max_tokens = params.get("requestedMaxTokens")
    requested = (
        math.floor(requested_max_tokens)
        if isinstance(requested_max_tokens, (int, float))
        and math.isfinite(requested_max_tokens)
        and requested_max_tokens > 0
        else None
    )
    if model_max is not None and requested is not None:
        return min(requested, model_max)
    return requested if requested is not None else model_max


def create_anthropic_vertex_stream_fn(project_id, region, base_url=None, deps=None):
    if deps is None:
        deps = _default_anthropic_vertex_stream_deps()
    client_options = {"region": region}
    if base_url:
        client_options["baseURL"] = base_url
    if project_id:
        client_options["projectId"] = project_id
    client = deps.AnthropicVertex(**client_options)

    def _stream(model, context, options=None):
        options = options or {}
        transport_model = {**model}
        max_tokens = _resolve_anthropic_vertex_max_tokens({
            "modelMaxTokens": transport_model.get("maxTokens"),
            "requestedMaxTokens": options.get("maxTokens"),
        })
        contract_model_id = resolve_claude_model_identity(model)
        fable5 = _is_claude_fable5_model(contract_model_id)
        mandatory_adaptive_thinking = fable5 or _is_claude_mythos5_model(contract_model_id)
        reasoning = options.get("reasoning") or ("high" if mandatory_adaptive_thinking else None)
        adaptive_thinking = mandatory_adaptive_thinking or bool(
            reasoning and _supports_adaptive_thinking(contract_model_id)
        )
        temperature = (
            None
            if adaptive_thinking
            or _is_claude_opus47_or_newer_model(contract_model_id)
            or _is_claude_mythos5_model(contract_model_id)
            else options.get("temperature")
        )
        opts: dict = {"client": client}
        if temperature is not None:
            opts["temperature"] = temperature
        if max_tokens is not None:
            opts["maxTokens"] = max_tokens
        opts["signal"] = options.get("signal")
        opts["cacheRetention"] = options.get("cacheRetention")
        opts["sessionId"] = options.get("sessionId")
        opts["headers"] = options.get("headers")
        opts["onPayload"] = options.get("onPayload")
        opts["maxRetryDelayMs"] = options.get("maxRetryDelayMs")
        opts["metadata"] = options.get("metadata")

        if reasoning:
            if _supports_adaptive_thinking(contract_model_id):
                opts["thinkingEnabled"] = True
                opts["effort"] = _map_anthropic_adaptive_effort(reasoning, transport_model, contract_model_id)
            else:
                opts["thinkingEnabled"] = True
                budgets = options.get("thinkingBudgets") or {}
                opts["thinkingBudgetTokens"] = budgets.get(reasoning, 10000)
        elif fable5:
            opts["thinkingEnabled"] = True
            opts["effort"] = "high"
        else:
            opts["thinkingEnabled"] = False

        return deps.streamAnthropic(transport_model, context, opts)

    return _stream


def _resolve_anthropic_vertex_sdk_base_url(base_url: Optional[str]) -> Optional[str]:
    if not base_url:
        return None
    trimmed = base_url.strip()
    if not trimmed:
        return None
    try:
        parsed = urlparse(trimmed)
        normalized_path = parsed.path.rstrip("/")
        if not normalized_path:
            new_path = "/v1"
            return urlunparse(parsed._replace(path=new_path)).rstrip("/")
        if not normalized_path.endswith("/v1"):
            new_path = f"{normalized_path}/v1"
            return urlunparse(parsed._replace(path=new_path)).rstrip("/")
        return trimmed
    except Exception:
        return trimmed


def create_anthropic_vertex_stream_fn_for_model(model, env=None, deps=None):
    import os

    if env is None:
        env = os.environ
    return create_anthropic_vertex_stream_fn(
        resolve_anthropic_vertex_project_id(env),
        resolve_anthropic_vertex_client_region({"baseUrl": model.get("baseUrl"), "env": env}),
        _resolve_anthropic_vertex_sdk_base_url(model.get("baseUrl")),
        deps,
    )
