"""Chutes OAuth PKCE login flow."""

from __future__ import annotations

import base64
import hashlib
import html
import secrets
import threading
import time
from collections.abc import Awaitable, Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from openclaw.packages.normalization_core import (
    normalize_optional_string,
    resolve_expires_at_ms_from_duration_seconds,
)
from openclaw.plugin_sdk.provider_web_search import read_response_text_limited

CHUTES_AUTHORIZE_ENDPOINT = "https://api.chutes.ai/idp/authorize"
CHUTES_TOKEN_ENDPOINT = "https://api.chutes.ai/idp/token"
CHUTES_USERINFO_ENDPOINT = "https://api.chutes.ai/idp/userinfo"
CHUTES_TOKEN_ERROR_BODY_LIMIT_BYTES = 8 * 1024


def _to_form_url_encoded(data: dict[str, str]) -> dict[str, str]:
    return data


def _generate_pkce_verifier_challenge() -> dict[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .decode("ascii")
        .rstrip("=")
    )
    return {"verifier": verifier, "challenge": challenge}


def _parse_redirect_uri(redirect_uri: str) -> dict[str, Any]:
    parsed = urlparse(redirect_uri)
    if parsed.scheme != "http":
        raise ValueError(f"Chutes OAuth redirect URI must be http:// (got {redirect_uri})")
    hostname = parsed.hostname or "127.0.0.1"
    if hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError(
            "Chutes OAuth redirect hostname must be loopback "
            f"(got {hostname}). Use http://127.0.0.1:<port>/..."
        )
    return {
        "hostname": hostname,
        "port": parsed.port or 80,
        "pathname": parsed.path or "/",
    }


def _parse_oauth_callback_input(
    input_value: str,
    expected_state: str,
    *,
    invalid_input: str = "Paste the full redirect URL (must include code + state).",
    missing_state: str = "Missing 'state' parameter. Paste the full redirect URL.",
) -> dict[str, str]:
    trimmed = input_value.strip()
    if not trimmed:
        raise ValueError(invalid_input)
    try:
        parsed = urlparse(trimmed)
        query = parse_qs(parsed.query)
        code_values = query.get("code") or []
        state_values = query.get("state") or []
        if not code_values or not code_values[0]:
            raise ValueError(invalid_input)
        if not state_values or not state_values[0]:
            raise ValueError(missing_state)
        code = code_values[0]
        state = state_values[0]
    except ValueError as error:
        if str(error) in (invalid_input, missing_state):
            raise
        raise ValueError(invalid_input) from error
    if state != expected_state:
        raise ValueError("OAuth state mismatch - possible CSRF attack. Please retry login.")
    return {"code": code, "state": state}


def _build_authorize_url(params: dict[str, Any]) -> str:
    query = urlencode(
        {
            "client_id": params["clientId"],
            "redirect_uri": params["redirectUri"],
            "response_type": "code",
            "scope": " ".join(params["scopes"]),
            "state": params["state"],
            "code_challenge": params["challenge"],
            "code_challenge_method": "S256",
        }
    )
    return f"{CHUTES_AUTHORIZE_ENDPOINT}?{query}"


def _resolve_chutes_expires_at(value: Any, now_ms: int) -> int | None:
    return resolve_expires_at_ms_from_duration_seconds(
        value,
        now_ms=now_ms,
        buffer_ms=5 * 60 * 1000,
        min_remaining_ms=30_000,
    )


async def _fetch_chutes_user_info(
    *,
    access_token: str,
    fetch_fn: Callable[..., Awaitable[Any]] | None = None,
) -> dict[str, Any] | None:
    fetch = fetch_fn
    if fetch is None:
        from openclaw.plugin_sdk.provider_http import default_fetch_fn as fetch

    response = await fetch(
        CHUTES_USERINFO_ENDPOINT,
        {"headers": {"Authorization": f"Bearer {access_token}"}},
    )
    if not getattr(response, "ok", False):
        return None
    data = await response.json()
    return data if isinstance(data, dict) else None


async def _exchange_chutes_code_for_tokens(params: dict[str, Any]) -> dict[str, Any]:
    fetch_fn = params.get("fetchFn")
    if fetch_fn is None:
        from openclaw.plugin_sdk.provider_http import default_fetch_fn as fetch_fn

    now_ms = params.get("now") if params.get("now") is not None else int(time.time() * 1000)
    app = params["app"]
    body_fields = _to_form_url_encoded(
        {
            "grant_type": "authorization_code",
            "client_id": app["clientId"],
            "code": params["code"],
            "redirect_uri": app["redirectUri"],
            "code_verifier": params["codeVerifier"],
        }
    )
    if app.get("clientSecret"):
        body_fields["client_secret"] = app["clientSecret"]
    body = urlencode(body_fields)

    response = await fetch_fn(
        CHUTES_TOKEN_ENDPOINT,
        {
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "body": body,
        },
    )
    if not getattr(response, "ok", False):
        detail = ""
        with __import__("contextlib").suppress(Exception):
            detail = await read_response_text_limited(
                response,
                CHUTES_TOKEN_ERROR_BODY_LIMIT_BYTES,
            )
        raise RuntimeError(f"Chutes token exchange failed: {detail}")

    data = await response.json()
    if not isinstance(data, dict):
        raise TypeError("Chutes token exchange returned invalid response")
    access = normalize_optional_string(data.get("access_token"))
    refresh = normalize_optional_string(data.get("refresh_token"))
    expires = _resolve_chutes_expires_at(data.get("expires_in"), now_ms)
    if not access:
        raise RuntimeError("Chutes token exchange returned no access_token")
    if not refresh:
        raise RuntimeError("Chutes token exchange returned no refresh_token")
    if expires is None:
        raise RuntimeError("Chutes token exchange returned invalid expires_in")

    info = await _fetch_chutes_user_info(access_token=access, fetch_fn=fetch_fn)
    result: dict[str, Any] = {
        "access": access,
        "refresh": refresh,
        "expires": expires,
        "email": info.get("username") if info else None,
        "accountId": info.get("sub") if info else None,
        "clientId": app["clientId"],
    }
    return result


async def _wait_for_local_oauth_callback(params: dict[str, Any]) -> dict[str, str]:
    hostname = params.get("hostname") or "localhost"
    timeout_ms = max(1, int(params["timeoutMs"]))
    expected_state = params["expectedState"]
    callback_path = params["callbackPath"]
    success_title = html.escape(str(params["successTitle"]))

    loop = __import__("asyncio").get_running_loop()
    future: __import__("asyncio").Future[dict[str, str]] = loop.create_future()

    class OAuthCallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            del format, args

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.end_headers()

        def do_GET(self) -> None:
            try:
                request_url = urlparse(self.path)
                if request_url.path != callback_path:
                    self.send_response(404)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"Not found")
                    return

                query = parse_qs(request_url.query)
                error = (query.get("error") or [None])[0]
                code = ((query.get("code") or [""])[0] or "").strip()
                state = ((query.get("state") or [""])[0] or "").strip()

                if error:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(f"Authentication failed: {error}".encode())
                    _finish(RuntimeError(f"OAuth error: {error}"))
                    return

                if not code or not state:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"Missing code or state")
                    _finish(RuntimeError("Missing OAuth code or state"))
                    return

                if state != expected_state:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"Invalid state")
                    _finish(RuntimeError("OAuth state mismatch"))
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
            except Exception as error:  # noqa: BLE001
                _finish(error if isinstance(error, Exception) else RuntimeError("OAuth callback failed"))

    server = HTTPServer((hostname, int(params["port"])), OAuthCallbackHandler)
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

    def _serve() -> None:
        on_progress = params.get("onProgress")
        if on_progress:
            on_progress(
                params.get("progressMessage")
                or f"Waiting for OAuth callback on {params['redirectUri']}..."
            )
        server.serve_forever(poll_interval=0.2)

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()

    def _on_timeout() -> None:
        _finish(RuntimeError("OAuth callback timeout"))

    loop.call_later(timeout_ms / 1000, _on_timeout)
    return await future


async def login_chutes(params: dict[str, Any]) -> dict[str, Any]:
    """Run Chutes OAuth and return refreshable stored credentials."""
    pkce = _generate_pkce_verifier_challenge()
    create_state = params.get("createState")
    state = create_state() if callable(create_state) else secrets.token_hex(16)
    timeout_ms = params.get("timeoutMs", 3 * 60 * 1000)
    app = params["app"]
    url = _build_authorize_url(
        {
            "clientId": app["clientId"],
            "redirectUri": app["redirectUri"],
            "scopes": app["scopes"],
            "state": state,
            "challenge": pkce["challenge"],
        }
    )

    if params.get("manual"):
        await params["onAuth"]({"url": url})
        on_progress = params.get("onProgress")
        if on_progress:
            on_progress("Waiting for redirect URL...")
        code_and_state = _parse_oauth_callback_input(
            await params["onPrompt"](
                {
                    "message": "Paste the redirect URL",
                    "placeholder": f"{app['redirectUri']}?code=...&state=...",
                }
            ),
            state,
        )
    else:
        redirect = _parse_redirect_uri(app["redirectUri"])

        async def _callback() -> dict[str, str]:
            return await _wait_for_local_oauth_callback(
                {
                    "expectedState": state,
                    "timeoutMs": timeout_ms,
                    "port": redirect["port"],
                    "callbackPath": redirect["pathname"],
                    "redirectUri": app["redirectUri"],
                    "successTitle": "Chutes OAuth complete",
                    "hostname": redirect["hostname"],
                    "onProgress": params.get("onProgress"),
                }
            )

        try:
            await params["onAuth"]({"url": url})
            code_and_state = await _callback()
        except Exception:  # noqa: BLE001
            on_progress = params.get("onProgress")
            if on_progress:
                on_progress("OAuth callback not detected; paste redirect URL...")
            code_and_state = _parse_oauth_callback_input(
                await params["onPrompt"](
                    {
                        "message": "Paste the redirect URL",
                        "placeholder": f"{app['redirectUri']}?code=...&state=...",
                    }
                ),
                state,
            )

    on_progress = params.get("onProgress")
    if on_progress:
        on_progress("Exchanging code for tokens...")
    return await _exchange_chutes_code_for_tokens(
        {
            "app": app,
            "code": code_and_state["code"],
            "codeVerifier": pkce["verifier"],
            "fetchFn": params.get("fetchFn"),
        }
    )
