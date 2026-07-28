from __future__ import annotations

import re
import time
from typing import Any, Callable

from .types import DIFF_ARTIFACT_ID_PATTERN, DIFF_ARTIFACT_TOKEN_PATTERN
from .viewer_assets import (
    LANGUAGE_PACK_VIEWER_ASSET_PREFIX,
    VIEWER_ASSET_PREFIX,
    get_served_language_pack_viewer_asset,
    get_served_viewer_asset,
)

VIEW_PREFIX = "/plugins/diffs/view/"
VIEWER_MAX_FAILURES_PER_WINDOW = 40
VIEWER_FAILURE_WINDOW_MS = 60_000
VIEWER_LOCKOUT_MS = 60_000
VIEWER_LIMITER_MAX_KEYS = 2048

VIEWER_CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'none'",
    "script-src 'self'",
    "style-src 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self' data:",
    "connect-src 'none'",
    "base-uri 'none'",
    "frame-ancestors 'self'",
    "object-src 'none'",
])


def _normalize_lowercase_string_or_empty(value: str | None) -> str:
    if not value:
        return ""
    return value.lower()


def _is_loopback_client_ip(client_ip: str) -> bool:
    return client_ip in ("127.0.0.1", "::1")


def _has_proxy_forwarding_hints(headers: dict[str, str]) -> bool:
    return any(
        headers.get(h)
        for h in (
            "x-forwarded-for",
            "x-real-ip",
            "forwarded",
            "x-forwarded-host",
            "x-forwarded-proto",
        )
    )


def _normalize_remote_client_key(remote_address: str | None) -> str:
    normalized = _normalize_lowercase_string_or_empty(remote_address)
    if not normalized:
        return "unknown"
    if normalized.startswith("::ffff:"):
        return normalized[len("::ffff:"):]
    return normalized


def _parse_request_url(raw_url: str | None) -> tuple[str, str] | None:
    if not raw_url:
        return None
    try:
        from urllib.parse import urlparse
        parsed = urlparse(raw_url)
        return parsed.path, parsed.query
    except Exception:
        return None


def _set_shared_headers(
    set_header: Callable[[str, str], None], content_type: str
) -> None:
    set_header("cache-control", "no-store, max-age=0")
    set_header("content-type", content_type)
    set_header("x-content-type-options", "nosniff")
    set_header("referrer-policy", "no-referrer")


class ViewerFailureLimiter:
    def __init__(self) -> None:
        self._failures: dict[str, dict[str, Any]] = {}

    def check(self, key: str) -> dict[str, Any]:
        self._prune()
        state = self._failures.get(key)
        if not state:
            return {"allowed": True, "retryAfterMs": 0}
        now = time.time() * 1000
        if state["lockUntilMs"] > now:
            return {"allowed": False, "retryAfterMs": state["lockUntilMs"] - now}
        if now - state["windowStartMs"] >= VIEWER_FAILURE_WINDOW_MS:
            del self._failures[key]
            return {"allowed": True, "retryAfterMs": 0}
        return {"allowed": True, "retryAfterMs": 0}

    def record_failure(self, key: str) -> None:
        self._prune()
        now = time.time() * 1000
        current = self._failures.get(key)
        if not current or now - current["windowStartMs"] >= VIEWER_FAILURE_WINDOW_MS:
            next_state: dict[str, Any] = {
                "windowStartMs": now,
                "failures": 1,
                "lockUntilMs": 0,
            }
        else:
            next_state = dict(current)
            next_state["failures"] = current["failures"] + 1
        if next_state["failures"] >= VIEWER_MAX_FAILURES_PER_WINDOW:
            next_state["lockUntilMs"] = now + VIEWER_LOCKOUT_MS
        self._failures[key] = next_state

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)

    def _prune(self) -> None:
        if len(self._failures) < VIEWER_LIMITER_MAX_KEYS:
            return
        now = time.time() * 1000
        keys_to_delete: list[str] = []
        for key, state in self._failures.items():
            if state["lockUntilMs"] <= now and now - state["windowStartMs"] >= VIEWER_FAILURE_WINDOW_MS:
                keys_to_delete.append(key)
            if len(self._failures) - len(keys_to_delete) < VIEWER_LIMITER_MAX_KEYS:
                break
        for key in keys_to_delete:
            del self._failures[key]
        if len(self._failures) >= VIEWER_LIMITER_MAX_KEYS:
            self._failures.clear()


def _resolve_viewer_access(
    headers: dict[str, str],
    remote_address: str | None,
    trusted_proxies: list[str] | None = None,
    allow_real_ip_fallback: bool = False,
) -> dict[str, Any]:
    proxy_hints_present = _has_proxy_forwarding_hints(headers)
    client_ip = remote_address
    if proxy_hints_present or (trusted_proxies and len(trusted_proxies) > 0):
        forwarded_for = headers.get("x-forwarded-for", "")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        elif allow_real_ip_fallback:
            real_ip = headers.get("x-real-ip", "")
            if real_ip:
                client_ip = real_ip
    remote_key = _normalize_remote_client_key(client_ip or remote_address)
    local_request = not proxy_hints_present and isinstance(client_ip, str) and _is_loopback_client_ip(remote_key)
    return {"remoteKey": remote_key, "localRequest": local_request}


def create_diffs_http_handler(params: dict[str, Any]) -> Callable[..., Any]:
    store = params["store"]
    logger = params.get("logger")
    allow_remote_viewer = params.get("allowRemoteViewer", False)
    trusted_proxies = params.get("trustedProxies")
    allow_real_ip_fallback = params.get("allowRealIpFallback", False)
    resolve_access_config = params.get("resolveAccessConfig")

    viewer_failure_limiter = ViewerFailureLimiter()

    async def handler(req: dict[str, Any], res: dict[str, Any]) -> bool:
        parsed = _parse_request_url(req.get("url"))
        if not parsed:
            return False
        pathname = parsed[0]

        if pathname.startswith(VIEWER_ASSET_PREFIX):
            return await _serve_asset(req, res, pathname, logger)

        if not pathname.startswith(VIEW_PREFIX):
            return False

        access_config = {"allowRemoteViewer": allow_remote_viewer, "trustedProxies": trusted_proxies, "allowRealIpFallback": allow_real_ip_fallback}
        if resolve_access_config:
            resolved = resolve_access_config()
            if resolved:
                access_config = resolved

        access = _resolve_viewer_access(
            req.get("headers", {}),
            req.get("remoteAddress"),
            access_config.get("trustedProxies"),
            access_config.get("allowRealIpFallback", False),
        )
        if not access["localRequest"] and not access_config.get("allowRemoteViewer", False):
            _respond_text(res, 404, "Diff not found")
            return True

        method = (req.get("method", "GET") or "GET").upper()
        if method not in ("GET", "HEAD"):
            _respond_text(res, 405, "Method not allowed")
            return True

        if not access["localRequest"]:
            throttled = viewer_failure_limiter.check(access["remoteKey"])
            if not throttled.get("allowed", True):
                res["statusCode"] = 429
                _set_shared_headers(res.get("setHeader", lambda k, v: None), "text/plain; charset=utf-8")
                res["setHeader"]("Retry-After", str(max(1, int(throttled.get("retryAfterMs", 0) / 1000))))
                res["end"]("Too Many Requests")
                return True

        path_parts = [p for p in pathname.split("/") if p]
        artifact_id = path_parts[3] if len(path_parts) > 3 else None
        token = path_parts[4] if len(path_parts) > 4 else None

        id_pattern = re.compile(DIFF_ARTIFACT_ID_PATTERN)
        token_pattern = re.compile(DIFF_ARTIFACT_TOKEN_PATTERN)
        if not artifact_id or not token or not id_pattern.match(artifact_id) or not token_pattern.match(token):
            _record_remote_failure(viewer_failure_limiter, access)
            _respond_text(res, 404, "Diff not found")
            return True

        artifact = await store.get_artifact(artifact_id, token)
        if not artifact:
            _record_remote_failure(viewer_failure_limiter, access)
            _respond_text(res, 404, "Diff not found or expired")
            return True

        try:
            html = await store.read_html(artifact_id)
            _reset_remote_failures(viewer_failure_limiter, access)
            res["statusCode"] = 200
            _set_shared_headers(res.get("setHeader", lambda k, v: None), "text/html; charset=utf-8")
            res["setHeader"]("content-security-policy", VIEWER_CONTENT_SECURITY_POLICY)
            if method == "HEAD":
                res["end"]()
            else:
                res["end"](html)
            return True
        except Exception as e:
            _record_remote_failure(viewer_failure_limiter, access)
            if logger:
                logger.warn(f"Failed to serve diff artifact {artifact_id}: {e}")
            _respond_text(res, 500, "Failed to load diff")
            return True

    return handler


def _record_remote_failure(limiter: ViewerFailureLimiter, access: dict[str, Any]) -> None:
    if not access.get("localRequest", True):
        limiter.record_failure(access["remoteKey"])


def _reset_remote_failures(limiter: ViewerFailureLimiter, access: dict[str, Any]) -> None:
    if not access.get("localRequest", True):
        limiter.reset(access["remoteKey"])


async def _serve_asset(
    req: dict[str, Any],
    res: dict[str, Any],
    pathname: str,
    logger: Any,
) -> bool:
    method = (req.get("method", "GET") or "GET").upper()
    if method not in ("GET", "HEAD"):
        _respond_text(res, 405, "Method not allowed")
        return True

    try:
        asset = await get_served_viewer_asset(pathname)
        if not asset:
            asset = await get_served_language_pack_viewer_asset(pathname)
        if not asset:
            _respond_text(res, 404, "Asset not found")
            return True
        res["statusCode"] = 200
        _set_shared_headers(res.get("setHeader", lambda k, v: None), asset["contentType"])
        if method == "HEAD":
            res["end"]()
        else:
            body = asset["body"]
            if isinstance(body, bytes):
                body = body.decode("utf-8")
            res["end"](body)
        return True
    except Exception as e:
        if logger:
            logger.warn(f"Failed to serve diffs asset {pathname}: {e}")
        _respond_text(res, 500, "Failed to load asset")
        return True


def _respond_text(res: dict[str, Any], status_code: int, body: str) -> None:
    res["statusCode"] = status_code
    _set_shared_headers(res.get("setHeader", lambda k, v: None), "text/plain; charset=utf-8")
    res["end"](body)