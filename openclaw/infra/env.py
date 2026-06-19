"""Environment variable normalization and helpers."""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Iterable, Mapping, MutableMapping
from typing import Any

ENV_NORMALIZATION_KEY_GROUPS: tuple[tuple[str, ...], ...] = (("ZAI_API_KEY", "Z_AI_API_KEY"),)

_logged_env: set[str] = set()


def _normalize_lowercase_string_or_empty(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    trimmed = value.strip()
    return trimmed.lower() if trimmed else ""


def _format_env_value(value: str, redact: bool = False) -> str:
    if redact:
        return "<redacted>"
    single_line = re.sub(r"\s+", " ", value).strip()
    if len(single_line) <= 160:
        return single_line
    return f"{single_line[:160]}…"


def log_accepted_env_option(
    *,
    key: str,
    description: str,
    value: str | None = None,
    redact: bool = False,
    env: Mapping[str, str] | None = None,
) -> None:
    """Log an accepted env option once, with optional redaction."""
    env_map = env if env is not None else os.environ
    if is_pytest_runtime_env(env_map):
        return
    if key in _logged_env:
        return
    raw_value = value if value is not None else env_map.get(key)
    if not raw_value or not raw_value.strip():
        return
    _logged_env.add(key)
    from openclaw.infra.logging import get_logger

    logger = get_logger("env")
    logger.info(
        "env option accepted",
        key=key,
        value=_format_env_value(raw_value, redact),
        description=description,
    )


def normalize_zai_env(env: MutableMapping[str, str] | None = None) -> None:
    """Normalize legacy Z_AI_API_KEY into canonical ZAI_API_KEY."""
    target = env if env is not None else os.environ
    zai = (target.get("ZAI_API_KEY") or "").strip()
    legacy = (target.get("Z_AI_API_KEY") or "").strip()
    if not zai and legacy:
        target["ZAI_API_KEY"] = legacy


def expand_env_normalization_keys(keys: Iterable[str]) -> set[str]:
    """Expand env keys to include alias groups."""
    expanded: set[str] = set()
    for key in keys:
        expanded.update(resolve_env_normalization_keys(key))
    return expanded


def resolve_env_normalization_keys(key: str) -> tuple[str, ...]:
    """Resolve one env key to its canonical-first normalization group."""
    normalized_key = key.upper() if sys.platform == "win32" else key
    for group in ENV_NORMALIZATION_KEY_GROUPS:
        if normalized_key in group:
            return group
    return (normalized_key,)


def is_truthy_env_value(value: str | None = None) -> bool:
    """Interpret common human/operator truthy env strings."""
    if not isinstance(value, str):
        return False
    return _normalize_lowercase_string_or_empty(value) in {"1", "on", "true", "yes"}


def is_pytest_runtime_env(env: Mapping[str, str] | None = None) -> bool:
    """Detect pytest/test execution from env shape."""
    env_map = env if env is not None else os.environ
    return (
        env_map.get("PYTEST_CURRENT_TEST") is not None
        or env_map.get("PYTEST_VERSION") is not None
        or env_map.get("VITEST") in {"true", "1"}
        or env_map.get("NODE_ENV") == "test"
    )


def normalize_env(env: MutableMapping[str, str] | None = None) -> None:
    """Apply process-wide env normalization before runtime config is read."""
    normalize_zai_env(env)
