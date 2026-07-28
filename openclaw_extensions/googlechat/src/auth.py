from __future__ import annotations

import re
import time
from typing import Literal

from openclaw.plugin_sdk.string_coerce_runtime import normalize_lowercase_string_or_empty
from openclaw_extensions.googlechat.runtime_api import fetch_with_ssr_fguard
from openclaw_extensions.googlechat.src.accounts import ResolvedGoogleChatAccount
from openclaw_extensions.googlechat.src.google_auth_runtime import (
    get_google_auth_transport,
    load_google_auth_runtime,
    resolve_validated_google_chat_credentials,
)

CHAT_SCOPE = "https://www.googleapis.com/auth/chat.bot"
CHAT_ISSUER = "chat@system.gserviceaccount.com"
ADDON_ISSUER_PATTERN = re.compile(r"^service-\d+@gcp-sa-gsuiteaddons\.iam\.gserviceaccount\.com$")
CHAT_CERTS_URL = "https://www.googleapis.com/service_accounts/v1/metadata/x509/chat@system.gserviceaccount.com"

MAX_AUTH_CACHE_SIZE = 32

GoogleChatAudienceType = Literal["app-url", "project-number"]

_auth_cache: dict[str, dict] = {}
_cached_certs: dict | None = None
_verify_client_promise: object | None = None


async def _get_verify_client():
    global _verify_client_promise
    if _verify_client_promise is None:
        async def _create():
            try:
                runtime = await load_google_auth_runtime()
                transport = await get_google_auth_transport()
                return runtime["OAuth2Client"](transporter=transport)
            except Exception as err:
                _verify_client_promise = None
                raise err

        _verify_client_promise = _create()
    return await _verify_client_promise


def _build_auth_key(account: ResolvedGoogleChatAccount) -> str:
    if account.credentials_file:
        return f"file:{account.credentials_file}"
    if account.credentials:
        import json
        return f"inline:{json.dumps(account.credentials)}"
    return "none"


async def _get_auth_instance(account: ResolvedGoogleChatAccount):
    key = _build_auth_key(account)
    cached = _auth_cache.get(account.account_id)
    if cached and cached.get("key") == key:
        return cached["auth"]

    runtime = await load_google_auth_runtime()
    transporter = await get_google_auth_transport()
    credentials = await resolve_validated_google_chat_credentials(account)

    if len(_auth_cache) > MAX_AUTH_CACHE_SIZE:
        oldest_key = next(iter(_auth_cache))
        _auth_cache.pop(oldest_key, None)

    GoogleAuth = runtime["GoogleAuth"]
    kwargs: dict = {"client_options": {"transporter": transporter}, "scopes": [CHAT_SCOPE]}
    if credentials:
        kwargs["credentials"] = credentials
    auth = GoogleAuth(**kwargs)
    _auth_cache[account.account_id] = {"key": key, "auth": auth}
    return auth


async def get_google_chat_access_token(account: ResolvedGoogleChatAccount) -> str:
    auth = await _get_auth_instance(account)
    client = await auth.get_client()
    access = await client.get_access_token()
    token = access if isinstance(access, str) else (access or {}).get("token")
    if not token:
        raise RuntimeError("Missing Google Chat access token")
    return token


async def _fetch_chat_certs() -> dict[str, str]:
    global _cached_certs
    now = time.time() * 1000
    if _cached_certs and now - _cached_certs.get("fetchedAt", 0) < 10 * 60 * 1000:
        return _cached_certs["certs"]

    result = await fetch_with_ssr_fguard({
        "url": CHAT_CERTS_URL,
        "auditContext": "googlechat.auth.certs",
    })
    response = result.get("response")
    release = result.get("release", lambda: None)
    try:
        if not response or not response.ok:
            raise RuntimeError(f"Failed to fetch Chat certs ({response.status if response else 0})")
        certs = await response.json()
        _cached_certs = {"fetchedAt": now, "certs": certs}
        return certs
    finally:
        if callable(release):
            await release()


async def verify_google_chat_request(params: dict) -> dict:
    bearer = (params.get("bearer") or "").strip()
    if not bearer:
        return {"ok": False, "reason": "missing token"}
    audience = (params.get("audience") or "").strip()
    if not audience:
        return {"ok": False, "reason": "missing audience"}
    audience_type = params.get("audienceType")

    if audience_type == "app-url":
        try:
            verify_client = await _get_verify_client()
            ticket = verify_client.verify_id_token(
                id_token=bearer,
                audience=audience,
            )
            payload = ticket.get_payload()
            email = normalize_lowercase_string_or_empty((payload or {}).get("email", ""))
            if not payload or not payload.get("email_verified"):
                return {"ok": False, "reason": "email not verified"}
            if email == CHAT_ISSUER:
                return {"ok": True}
            if not ADDON_ISSUER_PATTERN.match(email or ""):
                return {"ok": False, "reason": f"invalid issuer: {email}"}
            expected_principal = normalize_lowercase_string_or_empty(
                params.get("expectedAddOnPrincipal", "")
            )
            if not expected_principal:
                return {"ok": False, "reason": "missing add-on principal binding"}
            token_principal = normalize_lowercase_string_or_empty((payload or {}).get("sub", ""))
            if not token_principal or token_principal != expected_principal:
                return {
                    "ok": False,
                    "reason": f"unexpected add-on principal: {token_principal or '<missing>'}",
                }
            return {"ok": True}
        except Exception as err:
            return {"ok": False, "reason": str(err)}

    if audience_type == "project-number":
        try:
            verify_client = await _get_verify_client()
            certs = await _fetch_chat_certs()
            verify_client.verify_signed_jwt_with_certs(
                bearer, certs, audience, [CHAT_ISSUER]
            )
            return {"ok": True}
        except Exception as err:
            return {"ok": False, "reason": str(err)}

    return {"ok": False, "reason": "unsupported audience type"}


def _reset_google_chat_auth_for_tests():
    global _cached_certs, _verify_client_promise
    _auth_cache.clear()
    _cached_certs = None
    _verify_client_promise = None
    from openclaw_extensions.googlechat.src.google_auth_runtime import reset_google_auth_runtime_for_tests
    reset_google_auth_runtime_for_tests()


__all__ = [
    "get_google_chat_access_token",
    "verify_google_chat_request",
    "GoogleChatAudienceType",
    "CHAT_ISSUER",
    "CHAT_SCOPE",
    "testing",
]

testing = {"resetGoogleChatAuthForTests": _reset_google_chat_auth_for_tests}