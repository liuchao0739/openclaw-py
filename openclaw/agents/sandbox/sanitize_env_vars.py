"""Filter environment variables before sandbox propagation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Pattern

BLOCKED_ENV_VAR_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^ANTHROPIC_API_KEY$",
        r"^OPENAI_API_KEY$",
        r"^GEMINI_API_KEY$",
        r"^OPENROUTER_API_KEY$",
        r"^MINIMAX_API_KEY$",
        r"^ELEVENLABS_API_KEY$",
        r"^SYNTHETIC_API_KEY$",
        r"^TELEGRAM_BOT_TOKEN$",
        r"^DISCORD_BOT_TOKEN$",
        r"^SLACK_(BOT|APP)_TOKEN$",
        r"^LINE_CHANNEL_SECRET$",
        r"^LINE_CHANNEL_ACCESS_TOKEN$",
        r"^OPENCLAW_GATEWAY_(TOKEN|PASSWORD)$",
        r"^AWS_(SECRET_ACCESS_KEY|SECRET_KEY|SESSION_TOKEN)$",
        r"^(GH|GITHUB)_TOKEN$",
        r"^(AZURE|AZURE_OPENAI|COHERE|AI_GATEWAY|OPENROUTER)_API_KEY$",
        r"_?(API_KEY|TOKEN|PASSWORD|PRIVATE_KEY|SECRET)$",
    )
)

ALLOWED_ENV_VAR_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^LANG$",
        r"^LC_.*$",
        r"^PATH$",
        r"^HOME$",
        r"^USER$",
        r"^SHELL$",
        r"^TERM$",
        r"^TZ$",
        r"^NODE_ENV$",
    )
)


@dataclass
class EnvVarSanitizationResult:
    allowed: dict[str, str] = field(default_factory=dict)
    blocked: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_env_var_value(value: str) -> str | None:
    if "\0" in value:
        return "Contains null bytes"
    if len(value) > 32768:
        return "Value exceeds maximum length"
    if re.fullmatch(r"[A-Za-z0-9+/=]{80,}", value):
        return "Value looks like base64-encoded credential data"
    return None


def _matches_any(value: str, patterns: tuple[Pattern[str], ...]) -> bool:
    return any(p.search(value) for p in patterns)


def sanitize_env_vars(
    env_vars: dict[str, str | None],
    *,
    strict_mode: bool = False,
    custom_blocked_patterns: tuple[Pattern[str], ...] | None = None,
    custom_allowed_patterns: tuple[Pattern[str], ...] | None = None,
) -> EnvVarSanitizationResult:
    blocked_patterns = BLOCKED_ENV_VAR_PATTERNS + (custom_blocked_patterns or ())
    allowed_patterns = ALLOWED_ENV_VAR_PATTERNS + (custom_allowed_patterns or ())
    result = EnvVarSanitizationResult()

    for raw_key, value in env_vars.items():
        key = raw_key.strip()
        if not key or value is None:
            continue
        if _matches_any(key, blocked_patterns):
            result.blocked.append(key)
            continue
        if strict_mode and not _matches_any(key, allowed_patterns):
            result.blocked.append(key)
            continue
        warning = validate_env_var_value(value)
        if warning:
            if warning == "Contains null bytes":
                result.blocked.append(key)
                continue
            result.warnings.append(f"{key}: {warning}")
        result.allowed[key] = value

    return result


def sanitize_explicit_sandbox_env_vars(
    env_vars: dict[str, str | None],
) -> EnvVarSanitizationResult:
    result = EnvVarSanitizationResult()
    for raw_key, value in env_vars.items():
        key = raw_key.strip()
        if not key or value is None:
            continue
        warning = validate_env_var_value(value)
        if warning:
            if warning == "Contains null bytes":
                result.blocked.append(key)
                continue
            result.warnings.append(f"{key}: {warning}")
        result.allowed[key] = value
    return result