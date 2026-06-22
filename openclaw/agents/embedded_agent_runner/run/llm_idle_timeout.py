"""Wraps LLM streams with idle-timeout detection (timeout resolution ported)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from openclaw.agents.embedded_agent_runner.run.params import EmbeddedRunTrigger

DEFAULT_LLM_IDLE_TIMEOUT_MS = 120_000
MAX_TIMER_TIMEOUT_MS = 2_147_483_647


def _clamp_timer_timeout_ms(value_ms: float) -> int:
    if value_ms <= 0 or value_ms != value_ms:
        return 1
    return min(int(value_ms), MAX_TIMER_TIMEOUT_MS)


def _finite_seconds_to_ms(seconds: float | None) -> int | None:
    if seconds is None or seconds != seconds or seconds <= 0:
        return None
    return int(seconds * 1000)


def is_local_provider_base_url(base_url: str) -> bool:
    try:
        host = urlparse(base_url).hostname or ""
    except ValueError:
        return False
    host = host.lower()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if host in ("localhost", "0.0.0.0", "::1", "::ffff:7f00:1", "::ffff:127.0.0.1") or host.endswith(
        ".local"
    ):
        return True
    if re.match(r"^f[cd][0-9a-f]{2}:", host) or re.match(r"^fe[89ab][0-9a-f]:", host):
        return True
    if not re.match(r"^\d+\.\d+\.\d+\.\d+$", host):
        return False
    octets = [int(p) for p in host.split(".")]
    if any(p < 0 or p > 255 for p in octets):
        return False
    a, b = octets[0], octets[1]
    return (
        a == 127
        or a == 10
        or (a == 172 and 16 <= b <= 31)
        or (a == 192 and b == 168)
        or (a == 100 and 64 <= b <= 127)
    )


def _is_ollama_cloud_model(model: dict[str, Any] | None) -> bool:
    if not model:
        return False
    raw_id = model.get("id")
    if not isinstance(raw_id, str):
        return False
    provider = (model.get("provider") or "").strip().lower()
    if provider and not provider.startswith("ollama"):
        return False
    model_id = raw_id.strip().lower()
    slash = model_id.find("/")
    bare = model_id[slash + 1 :] if slash >= 0 else model_id
    return bare.endswith(":cloud")


def resolve_llm_idle_timeout_ms(
    *,
    cfg: dict[str, Any] | None = None,
    trigger: EmbeddedRunTrigger | None = None,
    run_timeout_ms: int | None = None,
    model_request_timeout_ms: int | None = None,
    model: dict[str, Any] | None = None,
) -> int:
    def clamp_implicit(value_ms: float) -> int:
        return _clamp_timer_timeout_ms(min(value_ms, DEFAULT_LLM_IDLE_TIMEOUT_MS))

    agent_timeout_ms = _finite_seconds_to_ms(
        ((cfg or {}).get("agents") or {}).get("defaults", {}).get("timeoutSeconds")
    )
    has_explicit_run = (
        isinstance(run_timeout_ms, (int, float))
        and run_timeout_ms == run_timeout_ms
        and run_timeout_ms > 0
    )
    run_is_no_timeout = has_explicit_run and run_timeout_ms >= MAX_TIMER_TIMEOUT_MS
    timeout_bounds = []
    if has_explicit_run and not run_is_no_timeout:
        timeout_bounds.append(run_timeout_ms)
    if not has_explicit_run and agent_timeout_ms is not None:
        timeout_bounds.append(agent_timeout_ms)
    timeout_bounds = [
        v
        for v in timeout_bounds
        if isinstance(v, (int, float)) and 0 < v < MAX_TIMER_TIMEOUT_MS
    ]

    if (
        isinstance(model_request_timeout_ms, (int, float))
        and model_request_timeout_ms == model_request_timeout_ms
        and model_request_timeout_ms > 0
    ):
        bounded = min(int(model_request_timeout_ms), *timeout_bounds) if timeout_bounds else int(
            model_request_timeout_ms
        )
        return _clamp_timer_timeout_ms(bounded)

    if has_explicit_run:
        if run_timeout_ms >= MAX_TIMER_TIMEOUT_MS:
            return 0
        if trigger == "cron":
            return _clamp_timer_timeout_ms(run_timeout_ms)  # type: ignore[arg-type]
        return clamp_implicit(run_timeout_ms)  # type: ignore[arg-type]

    if agent_timeout_ms is not None:
        return clamp_implicit(agent_timeout_ms)

    if trigger == "cron":
        return 0

    base_url = (model or {}).get("baseUrl")
    is_local = isinstance(base_url, str) and base_url and is_local_provider_base_url(base_url)
    if is_local and not _is_ollama_cloud_model(model):
        return 0

    return DEFAULT_LLM_IDLE_TIMEOUT_MS