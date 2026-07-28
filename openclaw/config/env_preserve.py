from __future__ import annotations

import os
from typing import Any


def restore_env_changes_if_unchanged(
    env: dict[str, str],
    before: dict[str, str],
    after: dict[str, str],
) -> bool:
    if before == after:
        return True
    for key in set(list(before.keys()) + list(after.keys())):
        if before.get(key) != after.get(key):
            if key in env and env.get(key) == after.get(key):
                if key in before:
                    env[key] = before[key]
                else:
                    env.pop(key, None)
    return True


def resolve_write_env_snapshot_for_path(
    actual_config_path: str | None = None,
    expected_config_path: str | None = None,
    env_snapshot_for_restore: dict[str, str] | None = None,
) -> dict[str, str] | None:
    return env_snapshot_for_restore


def snapshot_env(env: dict[str, str] | None = None) -> dict[str, str]:
    if env is None:
        env = os.environ
    return dict(env)
