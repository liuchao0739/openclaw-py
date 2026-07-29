"""Google Meet plugin module implements oauth behavior."""

from __future__ import annotations

import hashlib
import html
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from openclaw.packages.normalization_core import (
    MAX_DATE_TIMESTAMP_MS,
    normalize_optional_string,
    resolve_date_timestamp_ms,
    resolve_expires_at_ms_from_duration_seconds,
)
from openclaw.plugin_sdk.provider_http import default_fetch_fn
from openclaw.plugin_sdk.provider_web_search import read_response_text_limited
from openclaw_extensions.google_meet.src.google_api_errors import read_google_api_error_detail

GOOGLE_MEET_REDIRECT_URI = "http://localhost:8085/oauth2callback"
GOOGLE_MEET_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_MEET_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_MEET_TOKEN_HOST = "oauth2.googleapis.com"
GOOGLE_MEET_DEFAULT_TOKEN_LIFETIME_SECONDS = 3600
GOOGLE_MEET_SCOPES = [
    "https://www.googleapis.com/auth/meetings.space.created",
    "https://www.googleapis.com/auth/meetings.space.readonly",
    "https://www.googleapis.com/auth/meetings.space.settings",
    "https://www.googleapis.com/auth/meetings.conference.media.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly",
    "https://www.googleapis.com/auth/drive.meet.readonly",
]


def _resolve_google_meet_token_expires_at(value: Any, now_ms: int | None = None) -> int:
    now = resolve_date_timestamp_ms(now_ms if now_ms is not None else int(time.time() * 1000))
    if isinstance(value, (int, float)) and value <= 0:
        return now
    return (
        resolve_expires_at_ms_from_duration_seconds(value, now_ms=now)
        or resolve_expires_at_ms_from_duration_seconds(
            GOOGLE_MEET_DEFAULT_TOKEN_LIFETIME_SECONDS, now_ms=now
        )
        or now
    )


def build_google_meet_auth_url(params: dict[str, Any]) -> str:
    search = urlencode(
        {
            "client_id": params["clientId"],
            "response_type": "code",
            "redirect_uri": params.get("redirectUri", GOOGLE_MEET_REDIRECT_URI),
            "scope": " ".join(params.get("scopes", GOOGLE_MEET_SCOPES)),
            "code_challenge": params["challenge"],
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
            "state": params["state"],
        }
    )
    return f"{GOOGLE_MEET_AUTH_URL}?{search}"


async def _execute_google_token_request(body: str) -> dict[str, Any]:
    response = await default_fetch_fn(
        GOOGLE_MEET_TOKEN_URL,
        {
            "method": "POST",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Accept": "application/json",
            },
            "body": body,
        },
    )
    if not getattr(response, "ok", False):
        detail = await read_google_api_error_detail(response)
        status = getattr(response, "status", 0)
        raise Exception(f"Google OAuth token request failed ({status}): {detail}")
    payload = await response.json()
    if not isinstance(payload, dict):
        raise TypeError("Google OAuth token response was invalid")
    access_token = normalize_optional_string(payload.get("access_token"))
    if not access_token:
        raise Exception("Google OAuth token response was missing access_token")
    return {
        "accessToken": access_token,
        "expiresAt": _resolve_google_meet_token_expires_at(payload.get("expires_in")),
        "refreshToken": normalize_optional_string(payload.get("refresh_token")),
        "scope": normalize_optional_string(payload.get("scope")),
        "tokenType": normalize_optional_string(payload.get("token_type")),
    }


def _token_request_body(values: dict[str, str | None]) -> str:
    body: dict[str, str] = {}
    for key, value in values.items():
        if value and value.strip():
            body[key] = value
    return urlencode(body)


async def exchange_google_meet_auth_code(params: dict[str, Any]) -> dict[str, Any]:
    return await _execute_google_token_request(
        _token_request_body(
            {
                "client_id": params["clientId"],
                "client_secret": params.get("clientSecret"),
                "code": params["code"],
                "grant_type": "authorization_code",
                "redirect_uri": params.get("redirectUri", GOOGLE_MEET_REDIRECT_URI),
                "code_verifier": params["verifier"],
            }
        )
    )


async def refresh_google_meet_access_token(params: dict[str, Any]) -> dict[str, Any]:
    return await _execute_google_token_request(
        _token_request_body(
            {
                "client_id": params["clientId"],
                "client_secret": params.get("clientSecret"),
                "grant_type": "refresh_token",
                "refresh_token": params["refreshToken"],
            }
        )
    )


def _should_use_cached_google_meet_access_token(params: dict[str, Any]) -> bool:
    now = params.get("now", int(time.time() * 1000))
    safety_window_ms = params.get("safetyWindowMs", 60_000)
    access_token = normalize_optional_string(params.get("accessToken"))
    expires_at = params.get("expiresAt")
    return bool(
        access_token
        and isinstance(expires_at, (int, float))
        and expires_at <= MAX_DATE_TIMESTAMP_MS
        and expires_at > now + safety_window_ms
    )


async def resolve_google_meet_access_token(params: dict[str, Any]) -> dict[str, Any]:
    if _should_use_cached_google_meet_access_token(params):
        return {
            "accessToken": normalize_optional_string(params["accessToken"]),
            "expiresAt": params.get("expiresAt"),
            "refreshed": False,
        }
    if not normalize_optional_string(params.get("clientId")) or not normalize_optional_string(
        params.get("refreshToken")
    ):
        raise Exception(
            "Missing Google Meet OAuth credentials. Configure oauth.clientId and "
            "oauth.refreshToken, or pass --client-id and --refresh-token."
        )
    refreshed = await refresh_google_meet_access_token(
        {
            "clientId": params["clientId"],
            "clientSecret": params.get("clientSecret"),
            "refreshToken": params["refreshToken"],
        }
    )
    return {
        "accessToken": refreshed["accessToken"],
        "expiresAt": refreshed["expiresAt"],
        "refreshed": True,
    }


def create_google_meet_pkce() -> dict[str, str]:
    verifier = secrets.token_hex(32)
    challenge = hashlib.sha256(verifier.encode("ascii")).hexdigest()
    return {"verifier": verifier, "challenge": challenge}


def create_google_meet_oauth_state() -> str:
    return secrets.token_hex(16)


def _parse_oauth_callback_input(
    input_value: str,
    expected_state: str,
) -> dict[str, str]:
    trimmed = input_value.strip()
    if not trimmed:
        raise ValueError("Paste the full redirect URL, not just the code.")
    parsed = urlparse(trimmed)
    query = parse_qs(parsed.query)
    code_values = query.get("code") or []
    state_values = query.get("state") or []
    if not code_values or not code_values[0]:
        raise ValueError("Paste the full redirect URL, not just the code.")
    if not state_values or not state_values[0]:
        raise ValueError("Missing 'state' parameter. Paste the full redirect URL.")
    code = code_values[0]
    state = state_values[0]
    if state != expected_state:
        raise ValueError("OAuth state mismatch - please try again")
    return {"code": code, "state": state}


async def _wait_for_local_oauth_callback(params: dict[str, Any]) -> dict[str, str]:
    import asyncio

    hostname = "localhost"
    expected_state = params["expectedState"]
    timeout_ms = max(1, int(params["timeoutMs"]))
    callback_path = "/oauth2callback"
    success_title = html.escape(str(params.get("successTitle", "Google Meet OAuth complete")))

    loop = asyncio.get_running_loop()
    future: asyncio.Future[dict[str, str]] = loop.create_future()

    class OAuthCallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            del format, args

        def do_GET(self) -> None:
            try:
                request_url = urlparse(self.path)
                if request_url.path != callback_path:
                    self.send_response(404)
                    self.end_headers()
                    return
                query = parse_qs(request_url.query)
                error = (query.get("error") or [None])[0]
                code = ((query.get("code") or [""])[0] or "").strip()
                state = ((query.get("state") or [""])[0] or "").strip()
                if error:
                    self.send_response(400)
                    self.end_headers()
                    _finish(Exception(f"OAuth error: {error}"))
                    return
                if not code or not state:
                    self.send_response(400)
                    self.end_headers()
                    _finish(Exception("Missing OAuth code or state"))
                    return
                if state != expected_state:
                    self.send_response(400)
                    self.end_headers()
                    _finish(Exception("OAuth state mismatch"))
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    (
                        "<!doctype html><html><head><meta charset='utf-8'/></head>"
                        f"<body><h2>{success_title}</h2>"
                        "<p>You can close this window and return to OpenClaw.</p></body></html>"
                    ).encode()
                )
                _finish(None, {"code": code, "state": state})
            except Exception as error:
                _finish(error if isinstance(error, Exception) else Exception("OAuth callback failed"))

    server = HTTPServer((hostname, 8085), OAuthCallbackHandler)
    settled = False

    def _finish(error: Exception | None, result: dict[str, str] | None = None) -> None:
        nonlocal settled
        if settled:
            return
        settled = True
        server.shutdown()
        if error is not None:
            loop.call_soon_threadsafe(future.set_exception, error)
        elif result is not None:
            loop.call_soon_threadsafe(future.set_result, result)

    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True)
    thread.start()
    loop.call_later(timeout_ms / 1000, lambda: _finish(Exception("OAuth callback timeout")))
    return await future


async def wait_for_google_meet_auth_code(params: dict[str, Any]) -> str:
    params["writeLine"](f"Open this URL in your browser:\n\n{params['authUrl']}\n")
    if params["manual"]:
        input_value = await params["promptInput"]("Paste the full redirect URL here: ")
        parsed = _parse_oauth_callback_input(input_value, params["state"])
        return parsed["code"]
    callback = await _wait_for_local_oauth_callback(
        {
            "expectedState": params["state"],
            "timeoutMs": params["timeoutMs"],
            "successTitle": "Google Meet OAuth complete",
        }
    )
    return callback["code"]
