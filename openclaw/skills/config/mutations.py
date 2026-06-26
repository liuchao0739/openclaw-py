"""Skill config mutation helpers update persisted skill settings.

Mirrors src/skills/config/mutations.ts. Self-contained port with inline
REDACTED_SENTINEL and normalize_secret_input.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

REDACTED_SENTINEL = "__REDACTED__"


def _normalize_secret_input(value: str) -> str:
    """Normalize a secret input string."""
    if not isinstance(value, str):
        return ""
    return value.strip()


def patch_skill_config_entry(
    cfg: dict[str, Any],
    skill_key: str,
    patch: Mapping[str, Any],
) -> dict[str, Any]:
    """Patch a skill config entry in a config dict (non-mutating)."""
    result = copy.deepcopy(cfg)
    skills = result.setdefault("skills", {})
    entries = dict(skills.get("entries", {}))
    current = dict(entries.get(skill_key, {}))

    if isinstance(patch.get("enabled"), bool):
        current["enabled"] = patch["enabled"]

    if isinstance(patch.get("apiKey"), str):
        trimmed = _normalize_secret_input(patch["apiKey"])
        if trimmed == REDACTED_SENTINEL:
            pass  # Keep stored secret on redacted round-trip
        elif trimmed:
            current["apiKey"] = trimmed
        else:
            current.pop("apiKey", None)

    env_patch = patch.get("env")
    if isinstance(env_patch, Mapping):
        next_env = dict(current.get("env", {}))
        for key, value in env_patch.items():
            trimmed_key = key.strip() if isinstance(key, str) else ""
            if not trimmed_key:
                continue
            trimmed_val = value.strip() if isinstance(value, str) else ""
            if trimmed_val == REDACTED_SENTINEL:
                continue
            if not trimmed_val:
                next_env.pop(trimmed_key, None)
            else:
                next_env[trimmed_key] = trimmed_val
        current["env"] = next_env

    entries[skill_key] = current
    skills["entries"] = entries
    return result
