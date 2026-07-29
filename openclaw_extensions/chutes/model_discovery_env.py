"""Environment helper for Chutes model discovery behavior in tests."""

from __future__ import annotations

import os
from typing import Mapping


def is_chutes_model_discovery_test_environment(
    env: Mapping[str, str] | None = None,
) -> bool:
    source = env if env is not None else os.environ
    return source.get("NODE_ENV") == "test" or source.get("VITEST") == "true"
