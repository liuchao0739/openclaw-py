from typing import Any, Optional
from urllib.parse import urlunparse, urlparse


def _resolve_hosted_plugin_surface_url(
    scheme: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    path: Optional[str] = None,
    **kwargs: Any,
) -> Optional[str]:
    if not host:
        return None
    resolved_scheme = scheme or "http"
    netloc = host
    if port:
        netloc = f"{host}:{port}"
    return urlunparse((resolved_scheme, netloc, path or "", "", "", ""))


def resolve_canvas_host_url(
    canvas_port: Optional[int] = None,
    scheme: Optional[str] = None,
    host: Optional[str] = None,
    path: Optional[str] = None,
    **kwargs: Any,
) -> Optional[str]:
    return _resolve_hosted_plugin_surface_url(
        scheme=scheme,
        host=host,
        port=canvas_port,
        path=path,
    )
