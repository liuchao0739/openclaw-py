import secrets
from typing import Optional
from urllib.parse import urlparse, urlunparse

CANVAS_CAPABILITY_PATH_PREFIX = "/__openclaw__/cap"
CANVAS_CAPABILITY_TTL_MS = 5 * 60 * 1000


def _normalize_plugin_capability_scoped_url(raw_url: str):
    parsed = urlparse(raw_url)
    path = parsed.path
    if not path.startswith(CANVAS_CAPABILITY_PATH_PREFIX + "/"):
        return None
    segments = path[len(CANVAS_CAPABILITY_PATH_PREFIX) + 1:].split("/")
    if len(segments) < 2:
        return None
    capability = segments[0]
    remaining = "/".join(segments[1:])
    return {
        "capability": capability,
        "path": "/" + remaining if remaining else "/",
        "host": parsed.hostname,
        "port": parsed.port,
        "scheme": parsed.scheme,
    }


def mint_canvas_capability_token() -> str:
    return secrets.token_urlsafe(32)


def build_canvas_scoped_host_url(base_url: str, capability: str) -> Optional[str]:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return None
    path = f"{CANVAS_CAPABILITY_PATH_PREFIX}/{capability}"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def normalize_canvas_scoped_url(raw_url: str):
    return _normalize_plugin_capability_scoped_url(raw_url)
