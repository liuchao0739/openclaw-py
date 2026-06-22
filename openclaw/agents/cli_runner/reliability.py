"""Watchdog and supervisor key helpers for CLI runner reliability."""

from __future__ import annotations

import os
from typing import Any, Literal

from openclaw.agents.cli_watchdog_defaults import (
    CLI_FRESH_WATCHDOG_DEFAULTS,
    CLI_RESUME_WATCHDOG_DEFAULTS,
    CLI_WATCHDOG_MIN_TIMEOUT_MS,
)
from openclaw.agents.lanes import AGENT_LANE_SUBAGENT

EmbeddedRunTrigger = Literal["cron", "message", "manual", "heartbeat"]


def _normalize_lower(value: str | None) -> str:
    return (value or "").strip().lower()


def _pick_watchdog_profile(
    backend: dict[str, Any],
    use_resume: bool,
    trigger: str | None,
    has_explicit_run_timeout: bool,
) -> dict[str, Any]:
    reliability = backend.get("reliability") or {}
    watchdog = reliability.get("watchdog") or {}
    configured = watchdog.get("resume") if use_resume else watchdog.get("fresh")
    if use_resume and not configured and (trigger == "cron" or has_explicit_run_timeout):
        defaults = CLI_FRESH_WATCHDOG_DEFAULTS
    elif use_resume:
        defaults = CLI_RESUME_WATCHDOG_DEFAULTS
    else:
        defaults = CLI_FRESH_WATCHDOG_DEFAULTS

    ratio_val = (configured or {}).get("noOutputTimeoutRatio")
    if not isinstance(ratio_val, (int, float)) or ratio_val != ratio_val:
        ratio = defaults["noOutputTimeoutRatio"]
    else:
        ratio = max(0.05, min(0.95, float(ratio_val)))

    min_val = (configured or {}).get("minMs")
    if not isinstance(min_val, (int, float)) or min_val != min_val:
        min_ms = defaults["minMs"]
    else:
        min_ms = max(CLI_WATCHDOG_MIN_TIMEOUT_MS, int(min_val))

    max_val = (configured or {}).get("maxMs")
    if not isinstance(max_val, (int, float)) or max_val != max_val:
        max_ms = defaults["maxMs"]
    else:
        max_ms = max(CLI_WATCHDOG_MIN_TIMEOUT_MS, int(max_val))

    no_output = (configured or {}).get("noOutputTimeoutMs")
    no_output_timeout_ms = None
    if isinstance(no_output, (int, float)) and no_output == no_output:
        no_output_timeout_ms = max(CLI_WATCHDOG_MIN_TIMEOUT_MS, int(no_output))

    return {
        "noOutputTimeoutMs": no_output_timeout_ms,
        "noOutputTimeoutRatio": ratio,
        "minMs": min(min_ms, max_ms),
        "maxMs": max(min_ms, max_ms),
    }


def resolve_cli_no_output_timeout_ms(
    *,
    backend: dict[str, Any],
    timeout_ms: int,
    use_resume: bool,
    trigger: str | None = None,
    run_timeout_override_ms: int | None = None,
) -> int:
    has_explicit = (
        isinstance(run_timeout_override_ms, (int, float))
        and run_timeout_override_ms == run_timeout_override_ms
        and run_timeout_override_ms > 0
    )
    profile = _pick_watchdog_profile(backend, use_resume, trigger, has_explicit)
    cap = max(CLI_WATCHDOG_MIN_TIMEOUT_MS, timeout_ms - 1_000)
    if profile["noOutputTimeoutMs"] is not None:
        return min(profile["noOutputTimeoutMs"], cap)
    computed = int(timeout_ms * profile["noOutputTimeoutRatio"])
    bounded = min(profile["maxMs"], max(profile["minMs"], computed))
    return min(bounded, cap)


def resolve_cli_run_timeout_override_ms(
    *,
    config: dict[str, Any] | None = None,
    lane: str | None = None,
    timeout_ms: int,
    run_timeout_override_ms: int | None = None,
) -> int | None:
    if run_timeout_override_ms is not None:
        return run_timeout_override_ms
    agents = (config or {}).get("agents") or {}
    defaults = agents.get("defaults") or {}
    configured = defaults.get("timeoutSeconds")
    has_configured = (
        lane != AGENT_LANE_SUBAGENT
        and isinstance(configured, (int, float))
        and configured == configured
        and configured > 0
    )
    return timeout_ms if has_configured else None


def build_cli_supervisor_scope_key(
    *,
    backend: dict[str, Any],
    backend_id: str,
    cli_session_id: str | None = None,
) -> str | None:
    command = backend.get("command") or ""
    command_token = _normalize_lower(os.path.basename(str(command)))
    backend_token = _normalize_lower(backend_id)
    session_token = (cli_session_id or "").strip()
    if not session_token:
        return None
    return f"cli:{backend_token}:{command_token}:{session_token}"