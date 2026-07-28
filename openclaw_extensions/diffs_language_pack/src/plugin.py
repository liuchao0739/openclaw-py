from __future__ import annotations

from typing import Any

from openclaw_extensions.diffs_language_pack.src.viewer_assets import (
    VIEWER_ASSET_PREFIX,
    get_served_viewer_asset,
)


def register_diffs_language_pack_plugin(api: Any) -> None:
    api.register_http_route({
        "path": "/plugins/diffs-language-pack",
        "auth": "plugin",
        "match": "prefix",
        "handler": _create_diffs_language_pack_http_handler(),
    })


def _create_diffs_language_pack_http_handler():
    async def handler(req: dict[str, Any], res: dict[str, Any]) -> bool:
        url = req.get("url")
        if not url:
            return False
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
        except Exception:
            return False
        pathname = parsed.path
        if not pathname.startswith(VIEWER_ASSET_PREFIX):
            return False
        method = (req.get("method", "GET") or "GET").upper()
        if method not in ("GET", "HEAD"):
            _respond_text(res, 405, "Method not allowed")
            return True
        asset = await get_served_viewer_asset(pathname)
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
    return handler


def _respond_text(res: dict[str, Any], status_code: int, body: str) -> None:
    res["statusCode"] = status_code
    _set_shared_headers(res.get("setHeader", lambda k, v: None), "text/plain; charset=utf-8")
    res["end"](body)


def _set_shared_headers(set_header: Any, content_type: str) -> None:
    set_header("cache-control", "no-store, max-age=0")
    set_header("content-type", content_type)
    set_header("x-content-type-options", "nosniff")
    set_header("referrer-policy", "no-referrer")