import asyncio
import os
import time
from pathlib import Path
from typing import Any, Optional, Callable, Set, TypedDict

from .a2ui_shared import (
    CANVAS_HOST_PATH,
    CANVAS_WS_PATH,
    inject_canvas_live_reload,
    is_a2ui_path,
)
from .file_resolver import normalize_url_path, resolve_file_within_root

CANVAS_LIVE_RELOAD_MAX_INBOUND_MESSAGE_BYTES = 64 * 1024


class CanvasHostOpts(TypedDict, total=False):
    runtime: dict
    rootDir: Optional[str]
    port: Optional[int]
    listenHost: Optional[str]
    allowInTests: Optional[bool]
    liveReload: Optional[bool]
    watchFactory: Optional[Callable]
    webSocketServerClass: Optional[Callable]


class CanvasHostHandlerOpts(TypedDict, total=False):
    runtime: dict
    rootDir: Optional[str]
    basePath: Optional[str]
    allowInTests: Optional[bool]
    liveReload: Optional[bool]
    watchFactory: Optional[Callable]
    webSocketServerClass: Optional[Callable]


class CanvasHostHandler(TypedDict, total=False):
    rootDir: str
    basePath: str
    handleHttpRequest: Callable
    handleUpgrade: Callable
    close: Callable


class CanvasHostServer(TypedDict, total=False):
    port: int
    rootDir: str
    close: Callable


def _is_truthy_env_value(value: Optional[str]) -> bool:
    if not value:
        return False
    return value.strip().lower() in ("1", "true", "yes", "on")


def _is_disabled_by_env() -> bool:
    if _is_truthy_env_value(os.environ.get("OPENCLAW_SKIP_CANVAS_HOST")):
        return True
    if os.environ.get("NODE_ENV") == "test":
        return True
    if os.environ.get("VITEST"):
        return True
    return False


def _resolve_state_dir() -> str:
    return os.environ.get("OPENCLAW_STATE_DIR") or os.path.expanduser("~/.openclaw")


def _resolve_user_path(path: str) -> str:
    return os.path.expanduser(path)


def _ensure_dir(dir_path: str) -> None:
    Path(dir_path).mkdir(parents=True, exist_ok=True)


def _normalize_base_path(raw_path: Optional[str]) -> str:
    trimmed = (raw_path or CANVAS_HOST_PATH).strip()
    try:
        normalized = normalize_url_path(trimmed or CANVAS_HOST_PATH)
    except Exception:
        normalized = normalize_url_path(CANVAS_HOST_PATH)
    if normalized == "/":
        return "/"
    return normalized.rstrip("/")


def _default_index_html() -> str:
    return """<!doctype html>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>OpenClaw Canvas</title>
<style>
  html, body { height: 100%; margin: 0; background: #000; color: #fff; font: 16px/1.4 -apple-system, BlinkMacSystemFont, system-ui, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
  .wrap { min-height: 100%; display: grid; place-items: center; padding: 24px; }
  .card { width: min(720px, 100%); background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.10); border-radius: 16px; padding: 18px 18px 14px; }
  .title { display: flex; align-items: baseline; gap: 10px; }
  h1 { margin: 0; font-size: 22px; letter-spacing: 0.2px; }
  .sub { opacity: 0.75; font-size: 13px; }
  .row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
  button { appearance: none; border: 1px solid rgba(255,255,255,0.14); background: rgba(255,255,255,0.10); color: #fff; padding: 10px 12px; border-radius: 12px; font-weight: 600; cursor: pointer; }
  button:active { transform: translateY(1px); }
  .ok { color: #24e08a; }
  .bad { color: #ff5c5c; }
  .log { margin-top: 14px; opacity: 0.85; font: 12px/1.4 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; white-space: pre-wrap; background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.08); padding: 10px; border-radius: 12px; }
</style>
<div class="wrap">
  <div class="card">
    <div class="title">
      <h1>OpenClaw Canvas</h1>
      <div class="sub">Interactive test page (auto-reload enabled)</div>
    </div>
    <div class="row">
      <button id="btn-hello">Hello</button>
      <button id="btn-time">Time</button>
      <button id="btn-photo">Photo</button>
      <button id="btn-dalek">Dalek</button>
    </div>
    <div id="status" class="sub" style="margin-top: 10px;"></div>
    <div id="log" class="log">Ready.</div>
  </div>
</div>
<script>
(() => {
  const logEl = document.getElementById("log");
  const statusEl = document.getElementById("status");
  const log = (msg) => { logEl.textContent = String(msg); };
  const hasIOS = () => !!(window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.openclawCanvasA2UIAction);
  const hasAndroid = () => !!((window.openclawCanvasA2UIAction && typeof window.openclawCanvasA2UIAction.postMessage === "function"));
  const hasHelper = () => typeof window.openclawSendUserAction === "function";
  const helperReady = hasHelper();
  statusEl.textContent = "";
  statusEl.appendChild(document.createTextNode("Bridge: "));
  const bridgeStatus = document.createElement("span");
  bridgeStatus.className = helperReady ? "ok" : "bad";
  bridgeStatus.textContent = helperReady ? "ready" : "missing";
  statusEl.appendChild(bridgeStatus);
  statusEl.appendChild(document.createTextNode(" · iOS=" + (hasIOS() ? "yes" : "no") + " · Android=" + (hasAndroid() ? "yes" : "no")));
  const onStatus = (ev) => {
    const d = ev && ev.detail || {};
    log("Action status: id=" + (d.id || "?") + " ok=" + String(!!d.ok) + (d.error ? (" error=" + d.error) : ""));
  };
  window.addEventListener("openclaw:a2ui-action-status", onStatus);
  function send(name, sourceComponentId) {
    if (!hasHelper()) { log("No action bridge found."); return; }
    const sendUserAction = typeof window.openclawSendUserAction === "function" ? window.openclawSendUserAction : undefined;
    const ok = sendUserAction({ name, surfaceId: "main", sourceComponentId, context: { t: Date.now() } });
    log(ok ? ("Sent action: " + name) : ("Failed to send action: " + name));
  }
  document.getElementById("btn-hello").onclick = () => send("hello", "demo.hello");
  document.getElementById("btn-time").onclick = () => send("time", "demo.time");
  document.getElementById("btn-photo").onclick = () => send("photo", "demo.photo");
  document.getElementById("btn-dalek").onclick = () => send("dalek", "demo.dalek");
})();
</script>
"""


async def _prepare_canvas_root(root_dir: str) -> str:
    _ensure_dir(root_dir)
    root_real = str(Path(root_dir).resolve())
    index_path = Path(root_real) / "index.html"
    if not index_path.exists():
        try:
            index_path.write_text(_default_index_html(), encoding="utf-8")
        except Exception:
            pass
    return root_real


def _resolve_default_canvas_root() -> str:
    candidates = [os.path.join(_resolve_state_dir(), "canvas")]
    for dir_path in candidates:
        if Path(dir_path).is_dir():
            return dir_path
    return candidates[0]


async def create_canvas_host_handler(opts: CanvasHostHandlerOpts) -> CanvasHostHandler:
    runtime = opts.get("runtime", {})
    base_path = _normalize_base_path(opts.get("basePath"))

    if _is_disabled_by_env() and opts.get("allowInTests") is not True:
        return {
            "rootDir": "",
            "basePath": base_path,
            "handleHttpRequest": lambda *a: asyncio.sleep(0, result=False),
            "handleUpgrade": lambda *a: False,
            "close": lambda: asyncio.sleep(0),
        }

    root_dir = _resolve_user_path(opts.get("rootDir") or _resolve_default_canvas_root())
    root_real = await _prepare_canvas_root(root_dir)

    live_reload = opts.get("liveReload") is not False
    test_mode = opts.get("allowInTests") is True
    reload_debounce_ms = 12 if test_mode else 75
    write_stability_threshold_ms = 12 if test_mode else 75
    write_poll_interval_ms = 5 if test_mode else 10

    sockets: Set[Any] = set()
    debounce_handle = None
    watcher = None
    watcher_closed = False

    def broadcast_reload():
        if not live_reload:
            return
        for ws in sockets:
            try:
                ws.send("reload")
            except Exception:
                pass

    def schedule_reload():
        nonlocal debounce_handle
        if debounce_handle:
            debounce_handle.cancel()
        debounce_handle = asyncio.get_event_loop().call_later(
            reload_debounce_ms / 1000, broadcast_reload
        )

    watch_factory = opts.get("watchFactory")
    if live_reload and watch_factory:
        try:
            watcher = watch_factory(root_real, {
                "ignoreInitial": True,
                "awaitWriteFinish": {
                    "stabilityThreshold": write_stability_threshold_ms,
                    "pollInterval": write_poll_interval_ms,
                },
                "usePolling": test_mode,
                "ignored": [],
            })
        except Exception:
            watcher = None

    if watcher:
        try:
            watcher.on("all", lambda *args: schedule_reload())
        except Exception:
            pass
        try:
            watcher.on("error", lambda err: runtime.get("error", lambda x: None)(
                f"Canvas host watcher error: {err}"
            ))
        except Exception:
            pass

    async def handle_http_request(req, res):
        url_raw = req.get("url") if isinstance(req, dict) else getattr(req, "url", None)
        if not url_raw:
            return False

        try:
            from urllib.parse import urlparse
            parsed = urlparse(url_raw)
            if parsed.path == CANVAS_WS_PATH:
                res["status"] = 426 if live_reload else 404
                res["headers"]["Content-Type"] = "text/plain; charset=utf-8"
                res["body"] = "upgrade required" if live_reload else "not found"
                return True

            url_path = parsed.path
            if base_path != "/":
                if url_path != base_path and not url_path.startswith(base_path + "/"):
                    return False
                url_path = "/" if url_path == base_path else url_path[len(base_path):] or "/"

            method = req.get("method", "GET") if isinstance(req, dict) else getattr(req, "method", "GET")
            if method not in ("GET", "HEAD"):
                res["status"] = 405
                res["headers"]["Content-Type"] = "text/plain; charset=utf-8"
                res["body"] = "Method Not Allowed"
                return True

            opened = await resolve_file_within_root(root_real, url_path)
            if not opened:
                if url_path == "/" or url_path.endswith("/"):
                    res["status"] = 404
                    res["headers"]["Content-Type"] = "text/html; charset=utf-8"
                    res["body"] = f'<!doctype html><meta charset="utf-8" /><title>OpenClaw Canvas</title><pre>Missing file.\\nCreate {root_dir}/index.html</pre>'
                    return True
                res["status"] = 404
                res["headers"]["Content-Type"] = "text/plain; charset=utf-8"
                res["body"] = "not found"
                return True

            try:
                data = await opened.read_file()
            finally:
                await opened.close()

            from .a2ui import _detect_mime
            real_path = opened._file_path
            lower = real_path.lower()
            mime = _detect_mime(real_path)

            res["headers"]["Cache-Control"] = "no-store"
            if mime == "text/html":
                html = data.decode("utf-8") if isinstance(data, bytes) else data
                res["headers"]["Content-Type"] = "text/html; charset=utf-8"
                res["body"] = inject_canvas_live_reload(html) if live_reload else html
                return True

            res["headers"]["Content-Type"] = mime
            res["body"] = data
            return True
        except Exception as err:
            runtime.get("error", lambda x: None)(f"Canvas host request failed: {err}")
            res["status"] = 500
            res["headers"]["Content-Type"] = "text/plain; charset=utf-8"
            res["body"] = "error"
            return True

    def handle_upgrade(req, socket, head):
        if not sockets and not live_reload:
            return False
        from urllib.parse import urlparse
        url_raw = req.get("url") if isinstance(req, dict) else getattr(req, "url", None)
        if not url_raw:
            return False
        parsed = urlparse(url_raw)
        if parsed.path != CANVAS_WS_PATH:
            return False
        return True

    async def close():
        nonlocal watcher_closed
        if debounce_handle:
            debounce_handle.cancel()
        watcher_closed = True
        if watcher:
            try:
                await watcher.close()
            except Exception:
                pass

    return {
        "rootDir": root_dir,
        "basePath": base_path,
        "handleHttpRequest": handle_http_request,
        "handleUpgrade": handle_upgrade,
        "close": close,
    }


async def start_canvas_host(opts) -> CanvasHostServer:
    if _is_disabled_by_env() and opts.get("allowInTests") is not True:
        return {"port": 0, "rootDir": "", "close": lambda: asyncio.sleep(0)}

    runtime = opts.get("runtime", {})
    handler = opts.get("handler")
    if handler is None:
        handler = await create_canvas_host_handler({
            "runtime": runtime,
            "rootDir": opts.get("rootDir"),
            "basePath": CANVAS_HOST_PATH,
            "allowInTests": opts.get("allowInTests"),
            "liveReload": opts.get("liveReload"),
            "watchFactory": opts.get("watchFactory"),
            "webSocketServerClass": opts.get("webSocketServerClass"),
        })
    owns_handler = opts.get("ownsHandler", opts.get("handler") is None)

    listen_host = opts.get("listenHost") or "127.0.0.1"
    port = opts.get("port")
    listen_port = port if isinstance(port, int) and port > 0 else 0

    server = await asyncio.start_server(
        lambda reader, writer: None,
        host=listen_host,
        port=listen_port,
    )

    bound_port = server.sockets[0].getsockname()[1] if server.sockets else 0
    runtime.get("log", lambda x: None)(
        f"canvas host listening on http://{listen_host}:{bound_port} (root {handler['rootDir']})"
    )

    async def close():
        if owns_handler:
            await handler["close"]()
        server.close()
        await server.wait_closed()

    return {"port": bound_port, "rootDir": handler["rootDir"], "close": close}
