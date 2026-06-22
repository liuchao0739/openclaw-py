"""Credential state classification for auth profiles."""

from __future__ import annotations

from typing import Literal

from openclaw.agents.auth_profiles.types import AuthProfileCredential, OAuthCredential
from openclaw.config.secrets import (
    MAX_DATE_TIMESTAMP_MS,
    coerce_secret_ref,
    normalize_secret_input_string,
)

AuthCredentialReasonCode = Literal[
    "ok",
    "missing_credential",
    "invalid_expires",
    "expired",
    "unresolved_ref",
]

DEFAULT_OAUTH_REFRESH_MARGIN_MS = 5 * 60 * 1000

TokenExpiryState = Literal["missing", "valid", "expiring", "expired", "invalid_expires"]


def resolve_token_expiry_state(
    expires: object,
    now: float | None = None,
    *,
    expiring_within_ms: int | None = None,
) -> TokenExpiryState:
    if now is None:
        import time

        now = time.time() * 1000
    if expires is None:
        return "missing"
    if not isinstance(expires, (int, float)):
        return "invalid_expires"
    if expires != expires or expires <= 0 or expires > MAX_DATE_TIMESTAMP_MS:  # noqa: PLR0124
        return "invalid_expires"
    remaining_ms = expires - now
    if remaining_ms <= 0:
        return "expired"
    margin = max(0, expiring_within_ms or 0)
    if margin > 0 and remaining_ms <= margin:
        return "expiring"
    return "valid"


def has_usable_oauth_credential(
    credential: OAuthCredential | None,
    *,
    now: float | None = None,
    refresh_margin_ms: int | None = None,
) -> bool:
    if not credential or credential.get("type") != "oauth":
        return False
    access = credential.get("access")
    if not isinstance(access, str) or not access.strip():
        return False
    if now is None:
        import time

        now = time.time() * 1000
    margin = max(0, refresh_margin_ms if refresh_margin_ms is not None else DEFAULT_OAUTH_REFRESH_MARGIN_MS)
    return (
        resolve_token_expiry_state(
            credential.get("expires"),
            now,
            expiring_within_ms=margin,
        )
        == "valid"
    )


def _has_configured_secret_ref(value: object) -> bool:
    return coerce_secret_ref(value) is not None


def _has_configured_secret_string(value: object) -> bool:
    return normalize_secret_input_string(value) is not None


def evaluate_stored_credential_eligibility(
    *,
    credential: AuthProfileCredential,
    now: float | None = None,
) -> dict[str, bool | AuthCredentialReasonCode]:
    if now is None:
        import time

        now = time.time() * 1000

    ctype = credential.get("type")
    if ctype == "api_key":
        has_key = _has_configured_secret_string(credential.get("key"))
        has_key_ref = _has_configured_secret_ref(credential.get("keyRef"))
        if not has_key and not has_key_ref:
            return {"eligible": False, "reasonCode": "missing_credential"}
        return {"eligible": True, "reasonCode": "ok"}

    if ctype == "token":
        has_token = _has_configured_secret_string(credential.get("token"))
        has_token_ref = _has_configured_secret_ref(credential.get("tokenRef"))
        if not has_token and not has_token_ref:
            return {"eligible": False, "reasonCode": "missing_credential"}
        expiry_state = resolve_token_expiry_state(credential.get("expires"), now)
        if expiry_state == "invalid_expires":
            return {"eligible": False, "reasonCode": "invalid_expires"}
        if expiry_state == "expired":
            return {"eligible": False, "reasonCode": "expired"}
        return {"eligible": True, "reasonCode": "ok"}

    if ctype == "oauth":
        if (
            normalize_secret_input_string(credential.get("access")) is None
            and normalize_secret_input_string(credential.get("refresh")) is None
        ):
            if credential.get("oauthRef"):
                return {"eligible": False, "reasonCode": "unresolved_ref"}
            return {"eligible": False, "reasonCode": "missing_credential"}
        return {"eligible": True, "reasonCode": "ok"}

    return {"eligible": False, "reasonCode": "missing_credential"}