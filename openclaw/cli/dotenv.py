from __future__ import annotations

import os
from typing import Any

from openclaw.packages.normalization_core import normalize_optional_string


def load_dotenv(env_file: str | None = None) -> dict[str, str]:
    import os.path

    path = env_file or os.path.join(os.getcwd(), ".env")
    if not os.path.isfile(path):
        return {}
    result: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            if key:
                result[key] = value
    return result


def apply_dotenv(env_file: str | None = None, override: bool = False) -> None:
    loaded = load_dotenv(env_file)
    for key, value in loaded.items():
        if override or key not in os.environ:
            os.environ[key] = value
