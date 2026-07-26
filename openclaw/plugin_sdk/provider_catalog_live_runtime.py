"""Live provider model catalog discovery with SSRF-guarded HTTP and short-lived caching."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

from openclaw.packages.normalization_core import normalize_optional_string
from openclaw.plugin_sdk.provider_catalog_shared import (
    clear_live_catalog_cache_for_tests,
    get_cached_live_catalog_value,
)
from openclaw.plugin_sdk.provider_http import fetch_with_timeout, read_response_with_limit

_log = logging.getLogger(__name__)

LIVE_MODEL_CATALOG_BODY_MAX_BYTES = 4 * 1024 * 1024

__all__ = [
    "LiveModelCatalogHttpError",
    "clear_live_catalog_cache_for_tests",
    "fetch_live_provider_model_rows",
    "get_cached_live_provider_model_rows",
    "ssrf_policy_from_http_base_url_allowed_hostname",
]


class LiveModelCatalogHttpError(Exception):
    """Raised when live model catalog discovery receives a non-success HTTP status."""

    def __init__(self, provider_id: str, status: int) -> None:
        super().__init__(f"{provider_id} model discovery failed: HTTP {status}")
        self.provider_id = provider_id
        self.status = status
        self.name = "LiveModelCatalogHttpError"


def ssrf_policy_from_http_base_url_allowed_hostname(endpoint: str) -> dict[str, Any]:
    hostname = urlparse(endpoint).hostname or ""
    return {"hostnameAllowlist": [hostname]} if hostname else {}


def _read_default_live_model_catalog_rows(body: Any) -> list[Any]:
    if isinstance(body, list):
        return body
    if isinstance(body, dict) and isinstance(body.get("data"), list):
        return body["data"]
    raise ValueError("Live model catalog response must be an array or { data: [] }")


async def _cancel_unread_response_body(response: Any) -> None:
    body = getattr(response, "body", None)
    reader = body.get_reader() if body is not None and hasattr(body, "get_reader") else None
    if reader is not None and not getattr(response, "bodyUsed", False):
        with __import__("contextlib").suppress(Exception):
            await reader.cancel()


async def _read_live_model_catalog_json(response: Any, timeout_ms: int) -> Any:
    buffer = await read_response_with_limit(
        response,
        LIVE_MODEL_CATALOG_BODY_MAX_BYTES,
    )
    return json.loads(buffer.decode("utf-8"))


async def _default_fetch_guard(params: dict[str, Any]) -> dict[str, Any]:
    from openclaw.plugin_sdk.provider_http import default_fetch_fn

    policy = params.get("policy") or {}
    hostname = urlparse(params["url"]).hostname or ""
    allowlist = policy.get("hostnameAllowlist") or []
    if allowlist and hostname not in allowlist:
        raise RuntimeError(f"Blocked hostname in guarded fetch: {hostname}")

    timeout_ms = params.get("timeoutMs", 5_000)
    response = await fetch_with_timeout(
        params["url"],
        params.get("init") or {},
        timeout_ms,
        default_fetch_fn,
    )

    async def release() -> None:
        return None

    return {"response": response, "release": release}


async def fetch_live_provider_model_rows(params: dict[str, Any]) -> list[Any]:
    fetch_guard = params.get("fetchGuard") or _default_fetch_guard
    timeout_ms = params.get("timeoutMs", 5_000)
    guarded = await fetch_guard(
        {
            "url": params["endpoint"],
            "init": {"headers": _build_headers(params)},
            "timeoutMs": timeout_ms,
            "policy": params.get("policy")
            or ssrf_policy_from_http_base_url_allowed_hostname(params["endpoint"]),
            "auditContext": params.get("auditContext") or f"{params['providerId']}-model-discovery",
        }
    )
    response = guarded["response"]
    release: Callable[[], Awaitable[None]] = guarded["release"]
    try:
        if not getattr(response, "ok", False):
            await _cancel_unread_response_body(response)
            raise LiveModelCatalogHttpError(params["providerId"], int(response.status))
        read_rows = params.get("readRows") or _read_default_live_model_catalog_rows
        return list(read_rows(await _read_live_model_catalog_json(response, timeout_ms)))
    finally:
        await release()


def _select_live_model_catalog_request_api_key(ctx: dict[str, Any]) -> str | None:
    for key in ("discoveryApiKey", "apiKey"):
        trimmed = normalize_optional_string(ctx.get(key))
        if trimmed:
            return trimmed
    return None


def _build_default_live_model_catalog_headers(ctx: dict[str, Any]) -> dict[str, str]:
    request_api_key = _select_live_model_catalog_request_api_key(ctx)
    headers = {"Accept": "application/json"}
    if request_api_key:
        headers["Authorization"] = f"Bearer {request_api_key}"
    return headers


def _build_headers(params: dict[str, Any]) -> dict[str, str]:
    build_request_headers = (
        params.get("buildRequestHeaders") or _build_default_live_model_catalog_headers
    )
    request_api_key = _select_live_model_catalog_request_api_key(params)
    headers = dict(
        build_request_headers(
            {
                "apiKey": normalize_optional_string(params.get("apiKey")),
                "discoveryApiKey": request_api_key,
            }
        )
    )
    if "accept" not in {key.lower() for key in headers}:
        headers["Accept"] = "application/json"
    return headers


def _live_model_catalog_auth_cache_key(params: dict[str, Any]) -> str | None:
    return _select_live_model_catalog_request_api_key(params)


async def get_cached_live_provider_model_rows(params: dict[str, Any]) -> list[Any]:
    cache_key_parts = params.get("cacheKeyParts") or [
        params["providerId"],
        "model-rows",
        params["endpoint"],
        _live_model_catalog_auth_cache_key(params),
    ]
    return await get_cached_live_catalog_value(
        key_parts=cache_key_parts,
        ttl_ms=params.get("ttlMs"),
        now=params.get("now"),
        load=lambda: fetch_live_provider_model_rows(params),
        should_cache=params.get("shouldCacheRows"),
    )
