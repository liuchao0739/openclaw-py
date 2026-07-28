from __future__ import annotations

from urllib.parse import urlparse, urlunparse

DEFAULT_GATEWAY_PORT = 18789


def build_viewer_url(config: object, viewer_path: str, base_url: str | None = None) -> str:
    base = (base_url or "").strip() or _resolve_gateway_base_url(config)
    normalized_base = normalize_viewer_base_url(base)
    if not viewer_path.startswith("/"):
        viewer_path = "/" + viewer_path
    parsed = urlparse(normalized_base)
    base_path = parsed.path if parsed.path != "/" else ""
    base_path = base_path.rstrip("/")
    parsed = parsed._replace(path=base_path + viewer_path, query="", fragment="")
    return urlunparse(parsed)


def normalize_viewer_base_url(raw: str, field_name: str = "baseUrl") -> str:
    try:
        parsed = urlparse(raw)
    except Exception:
        raise ValueError(f"Invalid {field_name}: {raw}")
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"{field_name} must use http or https: {raw}")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{field_name} must not include query/hash: {raw}")
    parsed = parsed._replace(query="", fragment="")
    path = parsed.path.rstrip("/")
    parsed = parsed._replace(path=path)
    result = urlunparse(parsed)
    return result.rstrip("/")


def _resolve_gateway_base_url(config: object) -> str:
    tls = _gateway_field(config, "tls")
    scheme = "https" if tls and _get_attr_or_item(tls, "enabled") else "http"
    port_val = _gateway_field(config, "port")
    port = port_val if isinstance(port_val, int) else DEFAULT_GATEWAY_PORT
    custom_host = ""
    bind = _gateway_field(config, "bind")
    if bind == "custom":
        custom_host = (_gateway_field(config, "customBindHost") or "").strip()
        if custom_host:
            return f"{scheme}://{custom_host}:{port}"
    return f"{scheme}://127.0.0.1:{port}"


def _gateway_field(config: object, key: str) -> Any:
    gateway = _get_attr_or_item(config, "gateway")
    if gateway is None and isinstance(config, dict):
        gateway = config.get("gateway")
    if isinstance(gateway, dict):
        return gateway.get(key)
    return _get_attr_or_item(gateway, key) if gateway is not None else None


def _get_attr_or_item(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)