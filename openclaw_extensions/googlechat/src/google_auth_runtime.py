from __future__ import annotations

import json
import os
import re
from typing import Any

from openclaw.plugin_sdk.media_runtime import parse_media_content_length
from openclaw.plugin_sdk.ssrf_runtime import (
    build_hostname_allowlist_policy_from_suffix_allowlist,
    fetch_with_ssr_fguard,
)
from openclaw_extensions.googlechat.src.accounts import ResolvedGoogleChatAccount

GOOGLE_AUTH_ALLOWED_HOST_SUFFIXES = ["accounts.google.com", "googleapis.com"]
GOOGLE_AUTH_POLICY = build_hostname_allowlist_policy_from_suffix_allowlist(
    GOOGLE_AUTH_ALLOWED_HOST_SUFFIXES
)
GOOGLE_AUTH_AUDIT_CONTEXT = "googlechat.auth.google-auth"
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_AUTH_PROVIDER_CERTS_URL = "https://www.googleapis.com/oauth2/v1/certs"
GOOGLE_AUTH_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_UNIVERSE_DOMAIN = "googleapis.com"
GOOGLE_CLIENT_CERTS_URL_PREFIX = "https://www.googleapis.com/robot/v1/metadata/x509/"
MAX_GOOGLE_AUTH_RESPONSE_BYTES = 1024 * 1024
MAX_GOOGLE_CHAT_SERVICE_ACCOUNT_FILE_BYTES = 64 * 1024

_google_auth_runtime_promise: object | None = None


def _as_nullable_object_record(value: Any) -> dict | None:
    if value is not None and isinstance(value, dict):
        return value
    return None


def _read_optional_trimmed_string(record: dict, field_name: str) -> str | None:
    value = record.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise RuntimeError(f'Google Chat service account field "{field_name}" must be a string')
    trimmed = value.strip()
    if not trimmed:
        raise RuntimeError(f'Google Chat service account field "{field_name}" cannot be empty')
    return trimmed


def _read_required_trimmed_string(record: dict, field_name: str) -> str:
    result = _read_optional_trimmed_string(record, field_name)
    if result is None:
        raise RuntimeError(f'Google Chat service account is missing "{field_name}"')
    return result


def _assert_exact_url_field(record: dict, field_name: str, expected_url: str) -> None:
    value = _read_optional_trimmed_string(record, field_name)
    if not value:
        return
    if value != expected_url:
        raise RuntimeError(
            f'Google Chat service account field "{field_name}" must be {expected_url}, got {value}'
        )


def _assert_url_prefix_field(record: dict, field_name: str, expected_prefix: str) -> None:
    value = _read_optional_trimmed_string(record, field_name)
    if not value:
        return
    if not value.startswith(expected_prefix):
        raise RuntimeError(
            f'Google Chat service account field "{field_name}" must start with {expected_prefix}, got {value}'
        )


def _validate_google_chat_service_account_credentials(credentials: dict) -> dict:
    type_val = _read_optional_trimmed_string(credentials, "type")
    if type_val and type_val != "service_account":
        raise RuntimeError(
            f'Google Chat credentials must use service_account auth, got "{type_val}" instead'
        )

    _read_required_trimmed_string(credentials, "client_email")
    _read_required_trimmed_string(credentials, "private_key")

    universe_domain = _read_optional_trimmed_string(credentials, "universe_domain")
    if universe_domain and universe_domain != GOOGLE_AUTH_UNIVERSE_DOMAIN:
        raise RuntimeError(
            f'Google Chat service account field "universe_domain" must be {GOOGLE_AUTH_UNIVERSE_DOMAIN}, got {universe_domain}'
        )

    _assert_exact_url_field(credentials, "auth_uri", GOOGLE_AUTH_URI)
    _assert_exact_url_field(credentials, "auth_provider_x509_cert_url", GOOGLE_AUTH_PROVIDER_CERTS_URL)
    _assert_exact_url_field(credentials, "token_uri", GOOGLE_AUTH_TOKEN_URI)
    _assert_url_prefix_field(credentials, "client_x509_cert_url", GOOGLE_CLIENT_CERTS_URL_PREFIX)

    return credentials


async def _read_credentials_file(file_path: str) -> dict:
    if not file_path:
        raise RuntimeError("Google Chat service account file path is empty")
    if not os.path.isfile(file_path):
        raise RuntimeError("Google Chat service account file must be a regular file.")
    file_size = os.path.getsize(file_path)
    if file_size > MAX_GOOGLE_CHAT_SERVICE_ACCOUNT_FILE_BYTES:
        raise RuntimeError(
            f"Google Chat service account file exceeds {MAX_GOOGLE_CHAT_SERVICE_ACCOUNT_FILE_BYTES} bytes."
        )
    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()
    if len(raw.encode("utf-8")) > MAX_GOOGLE_CHAT_SERVICE_ACCOUNT_FILE_BYTES:
        raise RuntimeError(
            f"Google Chat service account file exceeds {MAX_GOOGLE_CHAT_SERVICE_ACCOUNT_FILE_BYTES} bytes."
        )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError("Invalid Google Chat service account JSON.")
    if not isinstance(parsed, dict):
        raise RuntimeError("Google Chat service account file must contain a JSON object.")
    return parsed


def _sanitize_google_auth_init(init: dict | None = None) -> dict | None:
    if init is None:
        return None
    next_init = {k: v for k, v in init.items()
                 if k not in ("agent", "cert", "dispatcher", "fetchImplementation",
                              "key", "noProxy", "proxy")}
    return next_init


def _resolve_google_auth_dispatcher_policy(input_val, init: dict | None = None) -> dict:
    from urllib.parse import urlparse
    if isinstance(input_val, str):
        request_url = input_val
    else:
        request_url = input_val if isinstance(input_val, str) else str(input_val)

    next_init = _sanitize_google_auth_init(init)
    return {"init": next_init}


def _read_google_auth_proxy_env_value(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


def _resolve_google_auth_env_proxy_url(protocol: str) -> str | None:
    http_proxy = (
        _read_google_auth_proxy_env_value(os.environ.get("HTTP_PROXY"))
        or _read_google_auth_proxy_env_value(os.environ.get("http_proxy"))
    )
    https_proxy = (
        _read_google_auth_proxy_env_value(os.environ.get("HTTPS_PROXY"))
        or _read_google_auth_proxy_env_value(os.environ.get("https_proxy"))
    )
    if protocol == "https":
        return https_proxy or http_proxy
    return http_proxy


def create_google_auth_fetch(base_fetch=None):
    async def _fetch(input_val, init: dict | None = None):
        if isinstance(input_val, str):
            url = input_val
        else:
            url = str(input_val)
        guarded = _resolve_google_auth_dispatcher_policy(input_val, init)
        result = await fetch_with_ssr_fguard({
            "auditContext": GOOGLE_AUTH_AUDIT_CONTEXT,
            "policy": GOOGLE_AUTH_POLICY,
            "url": url,
            "init": guarded.get("init"),
            **({"fetchImpl": base_fetch} if base_fetch else {}),
        })
        response = result.get("response")
        release = result.get("release", lambda: None)
        try:
            data = await response.read() if response else b""
            return {
                "status": response.status if response else 0,
                "headers": dict(response.headers) if response else {},
                "body": data,
            }
        finally:
            if callable(release):
                await release()
    return _fetch


async def load_google_auth_runtime() -> dict:
    global _google_auth_runtime_promise
    if _google_auth_runtime_promise is None:
        async def _load():
            try:
                from google.auth import _default as google_auth_module
                from google.oauth2 import service_account as service_account_module
                return {
                    "GoogleAuth": google_auth_module.GoogleAuth,
                    "OAuth2Client": service_account_module.IDTokenClient,
                }
            except ImportError:
                raise RuntimeError(
                    "google-auth-library is not installed. Install it with: pip install google-auth"
                )
        _google_auth_runtime_promise = _load()
    return await _google_auth_runtime_promise


async def get_google_auth_transport():
    runtime = await load_google_auth_runtime()
    return {"runtime": runtime}


async def resolve_validated_google_chat_credentials(
    account: ResolvedGoogleChatAccount,
) -> dict | None:
    if account.credentials:
        return _validate_google_chat_service_account_credentials(account.credentials)
    if account.credentials_file:
        file_creds = await _read_credentials_file(account.credentials_file)
        return _validate_google_chat_service_account_credentials(file_creds)
    return None


def reset_google_auth_runtime_for_tests():
    global _google_auth_runtime_promise
    _google_auth_runtime_promise = None


testing = {
    "resetGoogleAuthRuntimeForTests": reset_google_auth_runtime_for_tests,
}