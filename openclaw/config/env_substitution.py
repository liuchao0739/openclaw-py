from __future__ import annotations

import os
import re
from typing import Any


def resolve_config_env_vars(
    value: Any,
    env: dict[str, str] | None = None,
    on_missing: str | None = None,
) -> Any:
    if env is None:
        env = os.environ

    if isinstance(value, str):
        def _replace(match):
            var_name = match.group(1)
            return env.get(var_name, match.group(0))

        return re.sub(r"\$\{([^}]+)\}", _replace, value)

    if isinstance(value, list):
        return [resolve_config_env_vars(item, env, on_missing) for item in value]

    if isinstance(value, dict):
        return {
            k: resolve_config_env_vars(v, env, on_missing)
            for k, v in value.items()
        }

    return value


def restore_env_var_refs(
    value: Any,
    authored: Any,
    env: dict[str, str] | None = None,
) -> Any:
    if env is None:
        env = os.environ

    if isinstance(value, str) and isinstance(authored, str):
        for var_name, var_value in env.items():
            if var_value and var_value in value:
                value = value.replace(var_value, f"${{{var_name}}}")
        return value

    if isinstance(value, list) and isinstance(authored, list):
        return [
            restore_env_var_refs(v, a, env)
            for v, a in zip(value, authored)
        ]

    if isinstance(value, dict) and isinstance(authored, dict):
        return {
            k: restore_env_var_refs(value.get(k), authored.get(k), env)
            for k in set(list(value.keys()) + list(authored.keys()))
        }

    return value
