"""Diffs Language Pack plugin module implements plugin behavior."""

from __future__ import annotations

from typing import Any, Protocol
from urllib.parse import urlparse

from openclaw_extensions.diffs_language_pack.api import OpenClawPluginApi
from openclaw_extensions.diffs_language_pack.src.viewer_assets import (
    VIEWER_ASSET_PREFIX,
    get_served_viewer_asset,
)


class HttpRequest(Protocol):
    method: str
    url: str | None


class HttpResponse(Protocol):
    status_code: int

    def set_header(self, name: str, value: str) -> None: ...

    def end(self, body: str | bytes | None = None) -> None: ...


def register_diffs_language_pack_plugin(api: OpenClawPluginApi) -> None:
    api.register_http_route(
        {
            "path": "/plugins/diffs-language-pack",
            "auth": "plugin",
            "match": "prefix",
            "handler": create_diffs_language_pack_http_handler(),
        }
    )


def create_diffs_language_pack_http_handler():
    async def handler(req: HttpRequest, res: HttpResponse) -> bool:
        parsed = parse_request_url(req.url)
        if parsed is None or not parsed.path.startswith(VIEWER_ASSET_PREFIX):
            return False
        if req.method not in ("GET", "HEAD"):
            respond_text(res, 405, "Method not allowed")
            return True

        asset = await get_served_viewer_asset(parsed.path)
        if asset is None:
            respond_text(res, 404, "Asset not found")
            return True

        res.status_code = 200
        set_shared_headers(res, asset.content_type)
        if req.method == "HEAD":
            res.end()
        else:
            res.end(asset.body)
        return True

    return handler


def parse_request_url(raw_url: str | None) -> Any | None:
    if not raw_url:
        return None
    try:
        return urlparse(raw_url)
    except ValueError:
        return None


def respond_text(res: HttpResponse, status_code: int, body: str) -> None:
    res.status_code = status_code
    set_shared_headers(res, "text/plain; charset=utf-8")
    res.end(body)


def set_shared_headers(res: HttpResponse, content_type: str) -> None:
    res.set_header("cache-control", "no-store, max-age=0")
    res.set_header("content-type", content_type)
    res.set_header("x-content-type-options", "nosniff")
    res.set_header("referrer-policy", "no-referrer")
