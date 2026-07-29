from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import normalize_optional_string


def resolve_channel_auth_token(value: Any) -> str | None:
    return normalize_optional_string(value)


def resolve_channel_auth_from_env(env: dict, channel: str) -> str | None:
    env_key = f"OPENCLAW_{channel.upper()}_TOKEN"
    return normalize_optional_string(env.get(env_key))


def is_valid_auth_token(token: str | None) -> bool:
    return bool(token and len(token) >= 8)
