"""Shared run helpers for retry limits, model reporting, and final text."""

from __future__ import annotations

import secrets
import time
from typing import Any

ANTHROPIC_MAGIC_STRING_TRIGGER_REFUSAL = "ANTHROPIC_MAGIC_STRING_TRIGGER_REFUSAL"
ANTHROPIC_MAGIC_STRING_REPLACEMENT = "ANTHROPIC MAGIC STRING TRIGGER REFUSAL (redacted)"

RUNTIME_AUTH_REFRESH_MARGIN_MS = 5 * 60 * 1000
RUNTIME_AUTH_REFRESH_RETRY_MS = 60 * 1000
RUNTIME_AUTH_REFRESH_MIN_DELAY_MS = 5 * 1000

MAX_SAME_MODEL_RATE_LIMIT_RETRIES = 3
SAME_MODEL_RATE_LIMIT_BACKOFF_STEP_MS = 10_000
SAME_MODEL_RATE_LIMIT_MAX_BACKOFF_MS = 60_000

DEFAULT_OVERLOAD_FAILOVER_BACKOFF_MS = 0
DEFAULT_MAX_OVERLOAD_PROFILE_ROTATIONS = 1
DEFAULT_MAX_RATE_LIMIT_PROFILE_ROTATIONS = 1

BASE_RUN_RETRY_ITERATIONS = 24
RUN_RETRY_ITERATIONS_PER_PROFILE = 8
MIN_RUN_RETRY_ITERATIONS = 32
MAX_RUN_RETRY_ITERATIONS = 160


def resolve_overload_failover_backoff_ms(cfg: dict[str, Any] | None = None) -> int:
    auth = (cfg or {}).get("auth") or {}
    cooldowns = auth.get("cooldowns") or {}
    return int(cooldowns.get("overloadedBackoffMs", DEFAULT_OVERLOAD_FAILOVER_BACKOFF_MS))


def resolve_same_model_rate_limit_backoff_ms(retries_so_far: int) -> int:
    delay = SAME_MODEL_RATE_LIMIT_BACKOFF_STEP_MS * (max(0, retries_so_far) + 1)
    return min(SAME_MODEL_RATE_LIMIT_MAX_BACKOFF_MS, delay)


def resolve_same_model_rate_limit_retry_delay_ms(
    *,
    retries_so_far: int,
    retry_after_seconds: float | None = None,
) -> int:
    backoff_ms = resolve_same_model_rate_limit_backoff_ms(retries_so_far)
    retry_after_ms = 0
    if retry_after_seconds is not None and retry_after_seconds == retry_after_seconds:
        retry_after_ms = int(max(0, retry_after_seconds) * 1000)
    return max(backoff_ms, min(SAME_MODEL_RATE_LIMIT_MAX_BACKOFF_MS, retry_after_ms))


def scrub_anthropic_refusal_magic(prompt: str) -> str:
    if ANTHROPIC_MAGIC_STRING_TRIGGER_REFUSAL not in prompt:
        return prompt
    return prompt.replace(ANTHROPIC_MAGIC_STRING_TRIGGER_REFUSAL, ANTHROPIC_MAGIC_STRING_REPLACEMENT)


def create_compaction_diag_id() -> str:
    return f"ovf-{int(time.time() * 1000):x}-{secrets.token_hex(2)}"


def resolve_max_run_retry_iterations(
    profile_candidate_count: int,
    cfg: dict[str, Any] | None = None,
    agent_id: str | None = None,
) -> int:
    agents = (cfg or {}).get("agents") or {}
    defaults = agents.get("defaults") or {}
    run_retries = defaults.get("runRetries") or {}
    if agent_id and cfg:
        for entry in agents.get("list") or []:
            if isinstance(entry, dict) and entry.get("id") == agent_id:
                run_retries = entry.get("runRetries") or run_retries
                break

    base = max(1, int(run_retries.get("base", BASE_RUN_RETRY_ITERATIONS)))
    per_profile = max(0, int(run_retries.get("perProfile", RUN_RETRY_ITERATIONS_PER_PROFILE)))
    min_limit = max(1, int(run_retries.get("min", MIN_RUN_RETRY_ITERATIONS)))
    max_limit = max(min_limit, int(run_retries.get("max", MAX_RUN_RETRY_ITERATIONS)))
    scaled = base + max(1, profile_candidate_count) * per_profile
    return min(max_limit, max(min_limit, scaled))


def _is_embedded_harness_provider(provider: str) -> bool:
    return provider.strip().lower() == "openclaw"


def resolve_reported_model_ref(
    *,
    provider: str,
    model: str,
    assistant: dict[str, Any] | None = None,
) -> dict[str, str]:
    assistant_provider = (assistant or {}).get("provider")
    assistant_model = (assistant or {}).get("model")
    ap = assistant_provider.strip() if isinstance(assistant_provider, str) else ""
    am = assistant_model.strip() if isinstance(assistant_model, str) else ""
    if not ap:
        return {"provider": provider, "model": am or model}
    if _is_embedded_harness_provider(ap):
        return {"provider": provider, "model": model}
    return {"provider": ap, "model": am or model}