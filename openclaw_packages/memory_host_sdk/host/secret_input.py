from __future__ import annotations

import os
from typing import Optional

from .secret_input_utils import (
    has_configured_secret_input as _has_configured_secret_input,
    normalize_env_secret_input_string,
    normalize_resolved_secret_input_string as _normalize_resolved,
    resolve_secret_input_ref,
)


def has_configured_memory_secret_input(value: object) -> bool:
    return _has_configured_secret_input(value)


def resolve_memory_secret_input_string(value: object, path: str) -> Optional[str]:
    ref = resolve_secret_input_ref(value)
    if ref and ref.get("source") == "env":
        env_value = normalize_env_secret_input_string(os.environ.get(ref.get("id", "")))
        if env_value:
            return env_value
    return _normalize_resolved(value, path)
