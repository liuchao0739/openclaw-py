"""Config value resolution helpers.

Resolves config values that may be strings, env var references, or functions.
"""

from __future__ import annotations

import os
from typing import Any


def resolve_config_value(value: Any, *, env: dict[str, str] | None = None) -> Any:
    """Resolve a config value that may reference environment variables.

    - Strings starting with ``env:`` are resolved from the environment.
    - Functions are called with no arguments to produce the value.
    - All other values pass through unchanged.
    """
    if callable(value):
        return value()
    if isinstance(value, str) and value.startswith("env:"):
        env_name = value[4:]
        env_map = env or os.environ
        return env_map.get(env_name, "")
    return value


def resolve_optional_config_value(
    value: Any,
    default: Any = None,
    *,
    env: dict[str, str] | None = None,
) -> Any:
    """Resolve an optional config value with a default."""
    resolved = resolve_config_value(value, env=env)
    if resolved is None or resolved == "":
        return default
    return resolved
