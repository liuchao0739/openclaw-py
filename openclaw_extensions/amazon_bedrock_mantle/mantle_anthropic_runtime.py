import re
from typing import Any, Callable, Dict, Optional


MANTLE_ANTHROPIC_BETA = "fine-grained-tool-streaming-2025-05-14"


def resolve_mantle_anthropic_base_url(base_url: str) -> str:
    trimmed = re.sub(r"/+$", "", base_url)
    if trimmed.endswith("/anthropic"):
        return trimmed
    if trimmed.endswith("/v1"):
        return f"{trimmed[:-3]}/anthropic"
    return f"{trimmed}/anthropic"


def requires_default_sampling(model_id: str) -> bool:
    return "claude-opus-4-7" in (model_id or "")


def is_claude_mythos_preview_model(model: Any) -> bool:
    values = []
    for attr in ("id", "name"):
        value = getattr(model, attr, None) if not isinstance(model, dict) else model.get(attr)
        if isinstance(value, str):
            values.append(value)
    if isinstance(model, dict):
        params = model.get("params") or {}
        canonical = params.get("canonicalModelId")
        if isinstance(canonical, str):
            values.append(canonical)
    else:
        params = getattr(model, "params", None) or {}
        canonical = getattr(params, "canonicalModelId", None)
        if isinstance(canonical, str):
            values.append(canonical)

    for value in values:
        normalized = re.sub(r"[\s_.:]+", "-", value.strip().lower())
        if re.search(r"(?:^|-)claude-mythos-preview(?=$|[^a-z0-9])", normalized):
            return True
    return False


def resolve_mantle_reasoning(model: Any, options: Optional[Dict[str, Any]] = None):
    if requires_default_sampling(getattr(model, "id", "") if not isinstance(model, dict) else model.get("id", "")):
        return None
    reasoning = None
    if options is not None:
        reasoning = options.get("reasoning")
    if reasoning is None and is_claude_mythos_preview_model(model):
        reasoning = "high"
    if not is_claude_mythos_preview_model(model):
        return reasoning
    if reasoning == "minimal":
        return "low"
    if reasoning in ("xhigh", "max"):
        return "high"
    return reasoning


def merge_headers(*header_sources) -> Dict[str, str]:
    merged: Dict[str, str] = {}
    for headers in header_sources:
        if headers:
            merged.update(headers)
    return merged


def build_mantle_anthropic_base_options(
    model: Any, options: Optional[Dict[str, Any]], api_key: str
) -> Dict[str, Any]:
    model_max_tokens = getattr(model, "maxTokens", None) if not isinstance(model, dict) else model.get("maxTokens")
    max_tokens = (options.get("maxTokens") if options else None) or min(model_max_tokens or 0, 32_000)
    return {
        "temperature": None if requires_default_sampling(
            getattr(model, "id", "") if not isinstance(model, dict) else model.get("id", "")
        ) else (options.get("temperature") if options else None),
        "maxTokens": max_tokens,
        "signal": options.get("signal") if options else None,
        "apiKey": api_key,
        "cacheRetention": options.get("cacheRetention") if options else None,
        "sessionId": options.get("sessionId") if options else None,
        "onPayload": options.get("onPayload") if options else None,
        "maxRetryDelayMs": options.get("maxRetryDelayMs") if options else None,
        "metadata": options.get("metadata") if options else None,
    }


def adjust_max_tokens_for_thinking(
    base_max_tokens: int,
    model_max_tokens: int,
    reasoning_level: str,
    custom_budgets: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    default_budgets = {
        "minimal": 1024,
        "low": 2048,
        "medium": 8192,
        "high": 16384,
        "xhigh": 16384,
        "max": 16384,
    }
    budgets = dict(default_budgets)
    if custom_budgets:
        budgets.update(custom_budgets)
    min_output_tokens = 1024
    thinking_budget = budgets[reasoning_level]
    max_tokens = min(base_max_tokens + thinking_budget, model_max_tokens)
    if max_tokens <= thinking_budget:
        thinking_budget = max(0, max_tokens - min_output_tokens)
    return {"maxTokens": max_tokens, "thinkingBudget": thinking_budget}


def create_mantle_anthropic_stream_fn(deps: Optional[Dict[str, Any]] = None) -> Callable:
    def stream_fn(model, context, options=None):
        api_key = (options.get("apiKey") if options else None) or ""

        def default_create_client(client_options):
            try:
                from anthropic import Anthropic
            except ImportError:
                raise RuntimeError("@anthropic-ai/sdk is not installed")
            return Anthropic(**client_options)

        create_client = (deps or {}).get("createClient", default_create_client)
        stream_fn_impl = (deps or {}).get("stream")
        base_url = getattr(model, "baseUrl", None) if not isinstance(model, dict) else model.get("baseUrl")
        model_headers = getattr(model, "headers", None) if not isinstance(model, dict) else model.get("headers")
        client = create_client(
            {
                "api_key": None,
                "auth_token": api_key,
                "base_url": resolve_mantle_anthropic_base_url(base_url or ""),
                "dangerously_allow_browser": True,
                "default_headers": merge_headers(
                    {
                        "accept": "application/json",
                        "anthropic-dangerous-direct-browser-access": "true",
                        "anthropic-beta": MANTLE_ANTHROPIC_BETA,
                    },
                    model_headers,
                    options.get("headers") if options else None,
                ),
            }
        )
        base = build_mantle_anthropic_base_options(model, options, api_key)
        reasoning = resolve_mantle_reasoning(model, options)

        if not reasoning:
            return stream_fn_impl(
                model,
                context,
                {**base, "client": client, "thinkingEnabled": False},
            )

        model_max_tokens = getattr(model, "maxTokens", 0) if not isinstance(model, dict) else model.get("maxTokens", 0)
        adjusted = adjust_max_tokens_for_thinking(
            base.get("maxTokens") or 0,
            model_max_tokens,
            reasoning,
            options.get("thinkingBudgets") if options else None,
        )
        payload = {
            **base,
            "client": client,
            "maxTokens": adjusted["maxTokens"],
            "thinkingEnabled": True,
            "thinkingBudgetTokens": adjusted["thinkingBudget"],
        }
        if is_claude_mythos_preview_model(model):
            payload["effort"] = reasoning
        return stream_fn_impl(model, context, payload)

    return stream_fn
