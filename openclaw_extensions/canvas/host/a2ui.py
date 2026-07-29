import os
import sys
from pathlib import Path
from typing import Optional

from .a2ui_shared import A2UI_PATH, CANVAS_HOST_PATH, CANVAS_WS_PATH, inject_canvas_live_reload, is_a2ui_path
from .file_resolver import resolve_file_within_root

_A2UI_ROOT_RETRY_NULL_AFTER_MS = 10_000

_cached_a2ui_root_real: Optional[str] = None
_resolving_a2ui_root = False
_cached_a2ui_resolved_at_ms = 0


def _detect_mime(file_path: str) -> str:
    import mimetypes
    lower = file_path.lower()
    if lower.endswith(".html") or lower.endswith(".htm"):
        return "text/html"
    if lower.endswith(".js"):
        return "application/javascript"
    if lower.endswith(".css"):
        return "text/css"
    if lower.endswith(".json"):
        return "application/json"
    if lower.endswith(".svg"):
        return "image/svg+xml"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".woff"):
        return "font/woff"
    if lower.endswith(".woff2"):
        return "font/woff2"
    if lower.endswith(".ttf"):
        return "font/ttf"
    if lower.endswith(".ico"):
        return "image/x-icon"
    guessed, _ = mimetypes.guess_type(file_path)
    return guessed or "application/octet-stream"


async def _resolve_a2ui_root() -> Optional[str]:
    here = Path(__file__).parent
    entry_dir = Path(sys.argv[0]).parent if len(sys.argv) > 1 and sys.argv[0] else None
    candidates = [
        here / "a2ui",
        here / "canvas-host" / "a2ui",
    ]
    if entry_dir:
        candidates.extend([entry_dir / "a2ui", entry_dir / "canvas-host" / "a2ui"])
    candidates.extend([
        here.parent.parent / "extensions" / "canvas" / "src" / "host" / "a2ui",
        here.parent / "extensions" / "canvas" / "src" / "host" / "a2ui",
        Path.cwd() / "extensions" / "canvas" / "src" / "host" / "a2ui",
        Path.cwd() / "dist" / "canvas-host" / "a2ui",
    ])
    if sys.executable:
        candidates.insert(0, Path(sys.executable).parent / "a2ui")

    for dir_path in candidates:
        try:
            index_path = dir_path / "index.html"
            bundle_path = dir_path / "a2ui.bundle.js"
            if index_path.exists() and bundle_path.exists():
                return str(dir_path.resolve())
        except Exception:
            pass
    return None


async def _resolve_a2ui_root_real() -> Optional[str]:
    import time
    global _cached_a2ui_root_real, _resolving_a2ui_root, _cached_a2ui_resolved_at_ms
    now_ms = int(time.time() * 1000)
    if _cached_a2ui_root_real is not None or (
        _cached_a2ui_root_real is None and now_ms - _cached_a2ui_resolved_at_ms >= _A2UI_ROOT_RETRY_NULL_AFTER_MS
    ):
        if not _resolving_a2ui_root:
            _resolving_a2ui_root = True
            root = await _resolve_a2ui_root()
            if root:
                _cached_a2ui_root_real = str(Path(root).resolve())
            _cached_a2ui_resolved_at_ms = now_ms
            _resolving_a2ui_root = False
    return _cached_a2ui_root_real


async def _handle_a2ui_http_request_with_root_resolver(
    req, res, resolve_root_real
) -> bool:
    url_raw = req.get("url") if isinstance(req, dict) else getattr(req, "url", None)
    if not url_raw:
        return False

    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url_raw)
    base_path = A2UI_PATH if is_a2ui_path(parsed.path) else None
    if not base_path:
        return False

    method = req.get("method", "GET") if isinstance(req, dict) else getattr(req, "method", "GET")
    if method not in ("GET", "HEAD"):
        res["status"] = 405
        res["headers"]["Content-Type"] = "text/plain; charset=utf-8"
        res["body"] = "Method Not Allowed"
        return True

    a2ui_root_real = await resolve_root_real()
    if not a2ui_root_real:
        res["status"] = 503
        res["headers"]["Content-Type"] = "text/plain; charset=utf-8"
        res["body"] = "A2UI assets not found"
        return True

    rel = parsed.path[len(base_path):]
    opened = await resolve_file_within_root(a2ui_root_real, rel or "/")
    if not opened:
        res["status"] = 404
        res["headers"]["Content-Type"] = "text/plain; charset=utf-8"
        res["body"] = "not found"
        return True

    try:
        real_path = opened._file_path
        mime = _detect_mime(real_path)
        res["headers"]["Cache-Control"] = "no-store"

        if method == "HEAD":
            res["headers"]["Content-Type"] = (
                "text/html; charset=utf-8" if mime == "text/html" else mime
            )
            res["body"] = b""
            return True

        if mime == "text/html":
            buf = await opened.read_file("utf-8")
            res["headers"]["Content-Type"] = "text/html; charset=utf-8"
            res["body"] = inject_canvas_live_reload(buf)
            return True

        res["headers"]["Content-Type"] = mime
        res["body"] = await opened.read_file()
        return True
    finally:
        await opened.close()


def create_a2ui_http_request_handler(root_dir: str):
    root_real_promise = None

    async def handler(req, res):
        nonlocal root_real_promise
        if root_real_promise is None:
            root_real_promise = str(Path(root_dir).resolve())
        return await _handle_a2ui_http_request_with_root_resolver(
            req, res, lambda: root_real_promise
        )

    return handler


async def handle_a2ui_http_request(req, res) -> bool:
    return await _handle_a2ui_http_request_with_root_resolver(
        req, res, _resolve_a2ui_root_real
    )
