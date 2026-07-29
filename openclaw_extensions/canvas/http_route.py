from typing import Optional

from .config import is_canvas_host_enabled, resolve_canvas_host_config
from .host.a2ui_shared import A2UI_PATH, CANVAS_HOST_PATH, CANVAS_WS_PATH
from .host.a2ui import handle_a2ui_http_request
from .host.server import create_canvas_host_handler, CanvasHostHandler


class CanvasHttpRouteHandler:
    def __init__(self):
        self._host_handler_promise = None

    async def _load_host_handler(self, config, plugin_config, runtime, allow_in_tests=False):
        if not is_canvas_host_enabled(config):
            return None
        if self._host_handler_promise is None:
            async def _create():
                host_config = resolve_canvas_host_config(
                    config=config, plugin_config=plugin_config
                )
                handler = await create_canvas_host_handler({
                    "runtime": runtime,
                    "rootDir": host_config.get("root"),
                    "basePath": CANVAS_HOST_PATH,
                    "allowInTests": allow_in_tests,
                    "liveReload": host_config.get("liveReload"),
                })
                return handler if handler.get("rootDir") else None
            self._host_handler_promise = _create()
        return await self._host_handler_promise

    async def handle_http_request(self, req, res, config, plugin_config, runtime, allow_in_tests=False):
        handler = await self._load_host_handler(config, plugin_config, runtime, allow_in_tests)
        if not handler:
            return False
        from urllib.parse import urlparse
        url_raw = req.get("url") if isinstance(req, dict) else getattr(req, "url", None)
        if not url_raw:
            return False
        parsed = urlparse(url_raw)
        if parsed.path == A2UI_PATH or parsed.path.startswith(A2UI_PATH + "/"):
            return await handle_a2ui_http_request(req, res)
        return await handler["handleHttpRequest"](req, res)

    async def handle_upgrade(self, req, socket, head, config, plugin_config, runtime, allow_in_tests=False):
        handler = await self._load_host_handler(config, plugin_config, runtime, allow_in_tests)
        if not handler:
            return False
        from urllib.parse import urlparse
        url_raw = req.get("url") if isinstance(req, dict) else getattr(req, "url", None)
        if not url_raw:
            return False
        parsed = urlparse(url_raw)
        if parsed.path != CANVAS_WS_PATH:
            return False
        return handler["handleUpgrade"](req, socket, head)

    async def close(self):
        if self._host_handler_promise is not None:
            handler = await self._host_handler_promise
            if handler:
                await handler["close"]()
        self._host_handler_promise = None


def create_canvas_http_route_handler(config, plugin_config=None, runtime=None, allow_in_tests=False):
    return CanvasHttpRouteHandler()
