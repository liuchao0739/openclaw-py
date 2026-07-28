from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

from openclaw.plugin_sdk.provider_auth import (
    ensure_auth_profile_store,
    upsert_auth_profile_with_lock,
)

CLIENT_ID = "Iv1.b507a08c87ecfe98"
DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_DEVICE_VERIFICATION_URL = "https://github.com/login/device"

GITHUB_DEVICE_ACCESS_DENIED = "github-device-access-denied"
GITHUB_DEVICE_EXPIRED = "github-device-expired"


class GitHubDeviceFlowError(Exception):
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


async def _post_github_device_flow_form(
    url: str,
    body: dict[str, str],
) -> dict[str, Any]:
    import urllib.request
    encoded_body = urllib.parse.urlencode(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=encoded_body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            if res.status != 200:
                raise RuntimeError(f"HTTP {res.status}")
            return json.loads(res.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"{url} failed: {e}")


async def _request_device_code(scope: str) -> dict[str, Any]:
    body = {"client_id": CLIENT_ID, "scope": scope}
    json_data = await _post_github_device_flow_form(DEVICE_CODE_URL, body)
    return _parse_device_code_response(json_data, int(time.time() * 1000))


def _parse_device_code_response(
    value: dict[str, Any],
    issued_at: int,
) -> dict[str, Any]:
    expires_in = value.get("expires_in")
    interval = value.get("interval", 5)
    expires_at = issued_at + int(expires_in) * 1000 if expires_in else issued_at + 900_000

    if (
        not isinstance(value.get("device_code"), str) or not value["device_code"]
        or not isinstance(value.get("user_code"), str) or not value["user_code"]
        or not isinstance(value.get("verification_uri"), str) or not value["verification_uri"]
        or not isinstance(expires_in, int)
    ):
        raise ValueError("GitHub device code response missing fields")

    return {
        "deviceCode": value["device_code"],
        "userCode": value["user_code"],
        "verificationUri": value["verification_uri"],
        "expiresInMs": int(expires_in) * 1000,
        "expiresAt": expires_at,
        "intervalMs": max(1, int(interval)) * 1000,
    }


async def _poll_for_access_token(
    device_code: str,
    interval_ms: int,
    expires_at: int,
) -> str:
    import urllib.parse
    body_base = {
        "client_id": CLIENT_ID,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }

    while int(time.time() * 1000) < expires_at:
        json_data = await _post_github_device_flow_form(ACCESS_TOKEN_URL, body_base)
        if "access_token" in json_data:
            return json_data["access_token"]

        err = json_data.get("error", "unknown")
        if err == "authorization_pending":
            await _sleep_device_poll_delay(interval_ms, expires_at)
            continue
        if err == "slow_down":
            await _sleep_device_poll_delay(interval_ms + 2000, expires_at)
            continue
        if err == "expired_token":
            raise GitHubDeviceFlowError(
                GITHUB_DEVICE_EXPIRED,
                "GitHub device code expired; run login again",
            )
        if err == "access_denied":
            raise GitHubDeviceFlowError(GITHUB_DEVICE_ACCESS_DENIED, "GitHub login cancelled")
        raise RuntimeError(f"GitHub device flow error: {err}")

    raise GitHubDeviceFlowError(
        GITHUB_DEVICE_EXPIRED,
        "GitHub device code expired; run login again",
    )


async def _sleep_device_poll_delay(delay_ms: int, expires_at: int) -> None:
    requested = max(1, int(delay_ms))
    target = min(int(time.time() * 1000) + requested, expires_at)
    while int(time.time() * 1000) < target:
        remaining = max(1, target - int(time.time() * 1000))
        await asyncio.sleep(min(remaining / 1000, 1))


def _normalize_github_device_verification_url(raw: str) -> str:
    try:
        from urllib.parse import urlparse
        parsed = urlparse(raw)
        if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.path != "/login/device":
            raise ValueError("unexpected URL")
        if parsed.username or parsed.password:
            raise ValueError("URL has userinfo")
    except Exception:
        raise ValueError("GitHub device flow returned an invalid verification URL")
    return GITHUB_DEVICE_VERIFICATION_URL


def _normalize_github_device_user_code(raw: str) -> str:
    user_code = raw.strip()
    if not user_code or len(user_code) > 64:
        raise ValueError("GitHub device flow returned an invalid user code")
    return user_code


async def run_github_copilot_device_flow(
    io: dict[str, Any],
) -> dict[str, Any]:
    device = await _request_device_code("read:user")
    verification_url = _normalize_github_device_verification_url(device["verificationUri"])
    user_code = _normalize_github_device_user_code(device["userCode"])
    await io["showCode"]({
        "verificationUrl": verification_url,
        "userCode": user_code,
        "expiresInMs": device["expiresInMs"],
    })

    try:
        if "openUrl" in io:
            await io["openUrl"](verification_url)
    except Exception:
        pass

    try:
        access_token = await _poll_for_access_token(
            device["deviceCode"],
            max(1000, device["intervalMs"]),
            device["expiresAt"],
        )
        return {"status": "authorized", "accessToken": access_token}
    except GitHubDeviceFlowError as e:
        if e.kind == GITHUB_DEVICE_ACCESS_DENIED:
            return {"status": "access_denied"}
        if e.kind == GITHUB_DEVICE_EXPIRED:
            return {"status": "expired"}
        raise
