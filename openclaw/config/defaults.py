from __future__ import annotations

import math
from typing import Any

from openclaw.config.agent_limits import (
    DEFAULT_AGENT_MAX_CONCURRENT,
    DEFAULT_SUBAGENT_ARCHIVE_AFTER_MINUTES,
    DEFAULT_SUBAGENT_MAX_CONCURRENT,
)
from openclaw.config.cron_limits import DEFAULT_CRON_MAX_CONCURRENT_RUNS

DEFAULT_CONTEXT_TOKENS = 128000

DEFAULT_MODEL_COST: dict[str, float] = {
    "input": 0,
    "output": 0,
    "cacheRead": 0,
    "cacheWrite": 0,
}
DEFAULT_MODEL_INPUT = ["text"]
DEFAULT_MODEL_MAX_TOKENS = 8192


def is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def resolve_model_cost(raw: dict[str, Any] | None = None) -> dict[str, float]:
    return {
        "input": raw.get("input", DEFAULT_MODEL_COST["input"]) if raw else DEFAULT_MODEL_COST["input"],
        "output": raw.get("output", DEFAULT_MODEL_COST["output"]) if raw else DEFAULT_MODEL_COST["output"],
        "cacheRead": raw.get("cacheRead", DEFAULT_MODEL_COST["cacheRead"]) if raw else DEFAULT_MODEL_COST["cacheRead"],
        "cacheWrite": raw.get("cacheWrite", DEFAULT_MODEL_COST["cacheWrite"]) if raw else DEFAULT_MODEL_COST["cacheWrite"],
    }


def resolve_normalized_provider_model_max_tokens(
    provider_id: str,
    model_id: str,
    context_window: int,
    raw_max_tokens: int,
) -> int:
    clamped = min(raw_max_tokens, context_window)
    if provider_id != "mistral" or clamped < context_window:
        return clamped
    from openclaw.config.paths import MISTRAL_SAFE_MAX_TOKENS_BY_MODEL
    safe = MISTRAL_SAFE_MAX_TOKENS_BY_MODEL.get(model_id, DEFAULT_MODEL_MAX_TOKENS)
    return min(safe, context_window)


def apply_message_defaults(cfg: dict[str, Any]) -> dict[str, Any]:
    messages = cfg.get("messages")
    if messages is not None and "ackReactionScope" in messages:
        return cfg
    next_messages = dict(messages) if messages else {}
    next_messages["ackReactionScope"] = "group-mentions"
    result = dict(cfg)
    result["messages"] = next_messages
    return result


def apply_session_defaults(
    cfg: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session = cfg.get("session")
    if not session or session.get("mainKey") is None:
        return cfg
    trimmed = str(session.get("mainKey", "")).strip()
    result = dict(cfg)
    result["session"] = dict(session)
    result["session"]["mainKey"] = "main"
    if trimmed and trimmed != "main":
        warn = (options or {}).get("warn", print)
        warn("session.mainKey is ignored; main session is always \"main\".")
    return result


def apply_talk_config_normalization(config: dict[str, Any]) -> dict[str, Any]:
    from openclaw.config.talk import normalize_talk_config
    return normalize_talk_config(config)


def apply_model_defaults(
    cfg: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mutated = False
    next_cfg = cfg
    provider_config = (next_cfg.get("models") or {}).get("providers")
    if provider_config:
        next_providers = dict(provider_config)
        for provider_id, provider in provider_config.items():
            models = provider.get("models")
            if not isinstance(models, list) or len(models) == 0:
                if provider != next_providers.get(provider_id):
                    next_providers[provider_id] = provider
                    mutated = True
                continue
            next_models = []
            provider_mutated = False
            for model in models:
                raw = dict(model) if isinstance(model, dict) else {}
                model_mutated = False
                raw_id = raw.get("id", "")
                raw_reasoning = raw.get("reasoning", False)
                if raw.get("reasoning") is None:
                    raw_reasoning = False
                if raw_reasoning != raw.get("reasoning"):
                    model_mutated = True
                input_val = raw.get("input", list(DEFAULT_MODEL_INPUT))
                if "input" not in raw:
                    model_mutated = True
                cost = resolve_model_cost(raw.get("cost"))
                raw_cost = raw.get("cost", {})
                cost_mutated = (
                    not raw_cost
                    or raw_cost.get("input") != cost["input"]
                    or raw_cost.get("output") != cost["output"]
                    or raw_cost.get("cacheRead") != cost["cacheRead"]
                    or raw_cost.get("cacheWrite") != cost["cacheWrite"]
                )
                if cost_mutated:
                    model_mutated = True
                context_window = raw.get("contextWindow")
                if not is_positive_number(context_window):
                    context_window = DEFAULT_CONTEXT_TOKENS
                if raw.get("contextWindow") != context_window:
                    model_mutated = True
                default_max = min(DEFAULT_MODEL_MAX_TOKENS, context_window)
                raw_max = raw.get("maxTokens")
                if not is_positive_number(raw_max):
                    raw_max = default_max
                max_tokens = min(int(raw_max), context_window) if is_positive_number(raw_max) else default_max
                if raw.get("maxTokens") != max_tokens:
                    model_mutated = True
                api = raw.get("api", provider.get("api"))
                if raw.get("api") != api:
                    model_mutated = True
                if not model_mutated:
                    next_models.append(model)
                    continue
                provider_mutated = True
                next_model = dict(raw)
                next_model["id"] = raw_id
                next_model["reasoning"] = raw_reasoning
                next_model["input"] = input_val
                next_model["cost"] = cost
                next_model["contextWindow"] = context_window
                next_model["maxTokens"] = max_tokens
                next_model["api"] = api
                next_models.append(next_model)
            if not provider_mutated:
                if provider != next_providers.get(provider_id):
                    next_providers[provider_id] = provider
                    mutated = True
                continue
            next_providers[provider_id] = dict(provider, models=next_models)
            mutated = True
        if mutated:
            next_cfg = dict(next_cfg, models=dict(next_cfg.get("models", {}), providers=next_providers))
    return next_cfg


def apply_agent_defaults(cfg: dict[str, Any]) -> dict[str, Any]:
    agents = cfg.get("agents")
    defaults = (agents or {}).get("defaults")
    has_max = isinstance((defaults or {}).get("maxConcurrent"), (int, float))
    has_sub_max = isinstance(((defaults or {}).get("subagents") or {}).get("maxConcurrent"), (int, float))
    has_sub_archive = isinstance(((defaults or {}).get("subagents") or {}).get("archiveAfterMinutes"), (int, float))
    if has_max and has_sub_max and has_sub_archive:
        return cfg
    mutated = False
    next_defaults = dict(defaults) if defaults else {}
    if not has_max:
        next_defaults["maxConcurrent"] = DEFAULT_AGENT_MAX_CONCURRENT
        mutated = True
    next_subagents = dict((defaults or {}).get("subagents", {}))
    if not has_sub_max:
        next_subagents["maxConcurrent"] = DEFAULT_SUBAGENT_MAX_CONCURRENT
        mutated = True
    if not has_sub_archive:
        next_subagents["archiveAfterMinutes"] = DEFAULT_SUBAGENT_ARCHIVE_AFTER_MINUTES
        mutated = True
    if not mutated:
        return cfg
    result = dict(cfg)
    result["agents"] = dict(agents or {})
    result["agents"]["defaults"] = dict(next_defaults, subagents=next_subagents)
    return result


def apply_cron_defaults(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = (cfg.get("cron") or {}).get("maxConcurrentRuns")
    if isinstance(raw, (int, float)) and math.isfinite(raw):
        return cfg
    result = dict(cfg)
    result["cron"] = dict(cfg.get("cron", {}), maxConcurrentRuns=DEFAULT_CRON_MAX_CONCURRENT_RUNS)
    return result


def apply_logging_defaults(cfg: dict[str, Any]) -> dict[str, Any]:
    logging = cfg.get("logging")
    if not logging:
        return cfg
    if logging.get("redactSensitive"):
        return cfg
    result = dict(cfg)
    result["logging"] = dict(logging, redactSensitive="tools")
    return result


def apply_compaction_defaults(cfg: dict[str, Any]) -> dict[str, Any]:
    defaults = (cfg.get("agents") or {}).get("defaults")
    if not defaults:
        return cfg
    compaction = defaults.get("compaction")
    if compaction and compaction.get("mode"):
        return cfg
    result = dict(cfg)
    result["agents"] = dict(cfg.get("agents", {}))
    result["agents"]["defaults"] = dict(defaults)
    result["agents"]["defaults"]["compaction"] = dict(compaction or {}, mode="safeguard")
    return result


def apply_context_pruning_defaults(
    cfg: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not (cfg.get("agents") or {}).get("defaults"):
        return cfg
    return cfg
