"""Normalize literal secrets on auth profile upsert."""

from __future__ import annotations

from openclaw.agents.auth_profiles.types import AuthProfileCredential
from openclaw.utils.normalize_secret_input import normalize_secret_input


def normalize_auth_profile_credential(
    credential: AuthProfileCredential,
) -> AuthProfileCredential:
    ctype = credential.get("type")
    if ctype == "api_key":
        key = credential.get("key")
        if not isinstance(key, str):
            return credential
        normalized = normalize_secret_input(key)
        out = {k: v for k, v in credential.items() if k != "key"}
        if normalized:
            out["key"] = normalized
        return out  # type: ignore[return-value]
    if ctype == "token":
        token = credential.get("token")
        if not isinstance(token, str):
            return credential
        normalized = normalize_secret_input(token)
        out = {k: v for k, v in credential.items() if k != "token"}
        if normalized:
            out["token"] = normalized
        return out  # type: ignore[return-value]
    return credential