"""Discord plugin module implements account token inspect behavior."""

from __future__ import annotations

from typing import Literal

from openclaw.config.secrets import coerce_secret_ref, normalize_secret_input_string

DiscordCredentialStatus = Literal["available", "configured_unavailable", "missing"]


def inspect_discord_configured_token(value: object) -> dict[str, str] | None:
    normalized = normalize_secret_input_string(value)
    if normalized:
        import re

        return {
            "token": re.sub(r"^Bot\s+", "", normalized, flags=re.IGNORECASE),
            "tokenSource": "config",
            "tokenStatus": "available",
        }
    if coerce_secret_ref(value) or (value is not None and value != ""):
        return {
            "token": "",
            "tokenSource": "config",
            "tokenStatus": "configured_unavailable",
        }
    return None


__all__ = ["inspect_discord_configured_token"]
