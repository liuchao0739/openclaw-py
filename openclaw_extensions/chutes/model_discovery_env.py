"""Environment helper for Chutes model discovery behavior in tests."""

from __future__ import annotations

import os
from collections.abc import Mapping


def is_chutes_model_discovery_test_environment(
    env: Mapping[str, str | None] | None = None,
) -> bool:
    """Return whether dynamic Chutes model discovery should use test behavior."""
    resolved_env = env if env is not None else os.environ
    return resolved_env.get("NODE_ENV") == "test" or resolved_env.get("VITEST") == "true"
