from __future__ import annotations

import os
from pathlib import Path
from typing import Any


CONFIG_ENV_VAR_PREFIX = "OPENCLAW_"


def get_config_env_var(name: str, default: str | None = None) -> str | None:
    full_name = f"{CONFIG_ENV_VAR_PREFIX}{name}"
    return os.environ.get(full_name, default)


def set_config_env_var(name: str, value: str | None) -> None:
    full_name = f"{CONFIG_ENV_VAR_PREFIX}{name}"
    if value is None:
        os.environ.pop(full_name, None)
    else:
        os.environ[full_name] = value


def get_all_config_env_vars() -> dict[str, str]:
    result = {}
    prefix = CONFIG_ENV_VAR_PREFIX.lower()
    for key, value in os.environ.items():
        if key.lower().startswith(prefix):
            result[key[len(CONFIG_ENV_VAR_PREFIX):]] = value
    return result
