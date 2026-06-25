"""ACP runtime options for command replies."""

from __future__ import annotations

from typing import Any


def resolve_acp_runtime_options(
    params: dict[str, Any],
) -> dict[str, Any]:
    """Resolve ACP runtime options from command params."""
    command = params.get("command", {})
    cfg = params.get("cfg", {})

    options: dict[str, Any] = {
        "timeoutMs": command.get("timeoutMs", 120_000),
        "maxTurns": command.get("maxTurns", 25),
    }

    # Merge config defaults
    agents_config = cfg.get("agents", {}) if cfg else {}
    defaults = agents_config.get("defaults", {}) if isinstance(agents_config, dict) else {}
    acp_defaults = defaults.get("acp", {}) if isinstance(defaults, dict) else {}

    if isinstance(acp_defaults, dict):
        if "timeoutMs" in acp_defaults:
            options["timeoutMs"] = acp_defaults["timeoutMs"]
        if "maxTurns" in acp_defaults:
            options["maxTurns"] = acp_defaults["maxTurns"]

    # Command overrides
    if command.get("timeoutMs") is not None:
        options["timeoutMs"] = command["timeoutMs"]
    if command.get("maxTurns") is not None:
        options["maxTurns"] = command["maxTurns"]

    return options


def normalize_acp_runtime_options(options: dict[str, Any]) -> dict[str, Any]:
    """Normalize and validate ACP runtime options."""
    normalized: dict[str, Any] = {}

    timeout_ms = options.get("timeoutMs", 120_000)
    if isinstance(timeout_ms, (int, float)) and timeout_ms > 0:
        normalized["timeoutMs"] = int(timeout_ms)
    else:
        normalized["timeoutMs"] = 120_000

    max_turns = options.get("maxTurns", 25)
    if isinstance(max_turns, (int, float)) and max_turns > 0:
        normalized["maxTurns"] = int(max_turns)
    else:
        normalized["maxTurns"] = 25

    return normalized
