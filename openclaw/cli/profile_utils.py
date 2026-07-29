from __future__ import annotations

import os
from typing import Any

from openclaw.packages.normalization_core import normalize_optional_string


def resolve_profile_env_profile(profile: str | None) -> dict[str, str]:
    if not profile:
        return {}
    return {"OPENCLAW_PROFILE": profile}


def resolve_profile_config_path(profile: str | None = None) -> str:
    base = os.environ.get("OPENCLAW_HOME") or os.path.expanduser("~/.openclaw")
    if not profile:
        return os.path.join(base, "config.yaml")
    return os.path.join(base, "profiles", profile, "config.yaml")
