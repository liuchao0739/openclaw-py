import hashlib
import ipaddress
import json as _json
import os
import re
import socket
import time
import urllib.parse
import urllib.request
from typing import Any, Callable, Optional


class SsrfBlockedError(Exception):
    pass


_BLOCKED_HOSTNAMES = {
    "localhost",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
}

_BLOCKED_ENV_KEYS = {"FIRECRAWL_API_KEY"}


def _is_private_ip(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        return True
    if ip.version == 4:
        if ip in ipaddress.ip_network("169.254.169.254/32"):
            return True
    return False


def is_private_ip_address(addr: str) -> bool:
    return _is_private_ip(addr)


def is_blocked_hostname_or_ip(hostname: str) -> bool:
    if not hostname:
        return True
    lower = hostname.lower().rstrip(".")
    if lower in _BLOCKED_HOSTNAMES:
        return True
    if lower.endswith(".local") or lower.endswith(".internal"):
        return True
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    addresses = {info[4][0] for info in addr_info}
    return any(_is_private_ip(a) for a in addresses)


def normalize_secret_input(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = re.sub(r"\s+", "", value)
        return cleaned or None
    if isinstance(value, dict):
        if value.get("source") == "env":
            env_id = str(value.get("id", "")).strip()
            if env_id and env_id in _BLOCKED_ENV_KEYS:
                return normalize_secret_input(os.environ.get(env_id))
        return None
    return None


def resolve_secret_input_string(value: Any, path: str = "", defaults: Any = None) -> dict:
    resolved = normalize_secret_input(value)
    if resolved:
        return {"status": "available", "value": resolved}
    if value is None or value == "":
        return {"status": "missing"}
    if isinstance(value, dict) and value.get("source"):
        return {"status": "blocked", "ref": value}
    return {"status": "missing"}


def can_resolve_env_secret_ref_in_read_only_path(cfg: Any = None, provider: Any = None, id: str = "") -> bool:
    return id in _BLOCKED_ENV_KEYS


def read_string_value(value: Any) -> Optional[str]:
    if isinstance(value, str) and value:
        return value
    return None


def read_positive_integer_param(params: dict, key: str, *, max: Optional[int] = None, message: Optional[str] = None) -> Optional[int]:
    if key not in params:
        return None
    value = params[key]
    if isinstance(value, bool):
        raise ValueError(message or f"{key} must be a positive integer")
    if isinstance(value, int) and value > 0:
        if max is not None and value > max:
            raise ValueError(message or f"{key} must be at most {max}")
        return value
    if isinstance(value, float) and value.is_integer() and value > 0:
        if max is not None and value > max:
            raise ValueError(message or f"{key} must be at most {max}")
        return int(value)
    raise ValueError(message or f"{key} must be a positive integer")


def read_non_negative_integer_param(params: dict, key: str, *, message: Optional[str] = None) -> Optional[int]:
    if key not in params:
        return None
    value = params[key]
    if isinstance(value, bool):
        raise ValueError(message or f"{key} must be a non-negative integer")
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and value.is_integer() and value >= 0:
        return int(value)
    raise ValueError(message or f"{key} must be a non-negative integer")


def read_string_param(params: dict, key: str, *, required: bool = False) -> Optional[str]:
    if key not in params:
        if required:
            raise ValueError(f"{key} is required")
        return None
    value = params[key]
    if isinstance(value, str) and value:
        return value
    if required:
        raise ValueError(f"{key} is required")
    return None


def read_string_array_param(params: dict, key: str) -> Optional[list]:
    if key not in params:
        return None
    value = params[key]
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return None


def normalize_cache_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def read_cache(cache: dict, key: str) -> Optional[dict]:
    entry = cache.get(key)
    if not entry:
        return None
    if entry["expires_at"] <= time.time() * 1000:
        cache.pop(key, None)
        return None
    return entry


def write_cache(cache: dict, key: str, value: Any, ttl_ms: int) -> None:
    now_ms = int(time.time() * 1000)
    cache[key] = {
        "value": value,
        "expires_at": now_ms + ttl_ms,
        "inserted_at": now_ms,
    }


def resolve_cache_ttl_ms(ttl_ms: Optional[int], default_minutes: int) -> int:
    if ttl_ms is not None and ttl_ms > 0:
        return ttl_ms
    return default_minutes * 60 * 1000


def resolve_positive_timeout_seconds(value: Optional[float], default: int) -> int:
    if value is not None and isinstance(value, (int, float)) and value == value and value > 0:
        return max(1, int(value))
    return default


def truncate_text(text: str, max_chars: int) -> dict:
    if max_chars > 0 and len(text) > max_chars:
        return {"text": text[:max_chars], "truncated": True}
    return {"text": text, "truncated": False}


def markdown_to_text(markdown: str) -> str:
    text = re.sub(r"^#{1,6}\s+", "", markdown, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_EXTERNAL_CONTENT_RE = re.compile(r"[<>]")


def wrap_web_content(content: str, source: str = "web_fetch") -> str:
    return content


def wrap_external_content(content: str, source: str = "web_fetch", include_warning: bool = False) -> str:
    return content


def json_result(value: Any) -> dict:
    return {"details": value}


def json_result_from_details(value: Any) -> dict:
    return {"details": value}


def enable_plugin_in_config(config: dict, plugin_id: str) -> dict:
    plugins = config.setdefault("plugins", {})
    entries = plugins.setdefault("entries", {})
    entry = entries.setdefault(plugin_id, {})
    entry["enabled"] = True
    return config


def create_web_search_provider_contract_fields(*, credential_path: str, search_credential: dict, configured_credential: dict) -> dict:
    return {
        "getConfiguredCredentialValue": lambda config: None,
        "getConfiguredCredentialFallback": lambda config: None,
        "setConfiguredCredentialValue": lambda config_target, value: None,
    }


def fetch_with_ssrf_guard(*, url: str, init: dict, timeout_ms: int, policy: Optional[dict] = None, audit_context: str = "") -> dict:
    method = init.get("method", "GET")
    headers = init.get("headers", {})
    body = init.get("body")
    req = urllib.request.Request(url, data=body.encode("utf-8") if isinstance(body, str) else body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout_ms / 1000)
        return {"response": resp, "release": (lambda: None)}
    except urllib.error.HTTPError as e:
        return {"response": e, "release": (lambda: None)}


def assert_ok_or_throw_provider_error(response: Any, label: str) -> None:
    status = getattr(response, "status", None) or getattr(response, "code", None)
    if status is not None and 200 <= status < 300:
        return
    detail = ""
    request_id = None
    try:
        raw = response.read(65536)
        if raw:
            try:
                payload = _json.loads(raw.decode("utf-8", errors="replace"))
                if isinstance(payload, dict):
                    detail = payload.get("message") or payload.get("error") or ""
                    request_id = payload.get("request_id")
            except Exception:
                detail = raw.decode("utf-8", errors="replace")
    except Exception:
        pass
    suffix = f" [request_id={request_id}]" if request_id else ""
    raise RuntimeError(f"{label} ({status}): {detail}{suffix}")


def read_response_with_limit(response: Any, max_bytes: int, on_overflow: Optional[Callable] = None) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = response.read(65536)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            if on_overflow:
                raise on_overflow({"maxBytes": max_bytes})
            raise RuntimeError(f"response exceeds {max_bytes} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


def read_response_text(response: Any, *, max_bytes: int = 65536) -> dict:
    data = response.read(max_bytes + 1)
    truncated = len(data) > max_bytes
    if truncated:
        data = data[:max_bytes]
    return {"text": data.decode("utf-8", errors="replace"), "truncated": truncated}


def read_provider_json_response(response: Any, label: str, *, max_bytes: Optional[int] = None) -> dict:
    limit = max_bytes or (16 * 1024 * 1024)
    data = response.read(limit + 1)
    if len(data) > limit:
        raise RuntimeError(f"{label}: JSON response exceeds {limit} bytes")
    try:
        return _json.loads(data.decode("utf-8", errors="replace"))
    except Exception:
        raise RuntimeError(f"{label}: malformed JSON response")


def with_self_hosted_web_tools_endpoint(options: dict, handler: Callable) -> Any:
    return _execute_endpoint(options, handler)


def with_strict_web_tools_endpoint(options: dict, handler: Callable) -> Any:
    return _execute_endpoint(options, handler)


def _execute_endpoint(options: dict, handler: Callable) -> Any:
    url = options["url"]
    timeout_seconds = options.get("timeoutSeconds", 30)
    init = options.get("init", {})
    method = init.get("method", "GET")
    headers = init.get("headers", {})
    body = init.get("body")
    req = urllib.request.Request(
        url,
        data=body.encode("utf-8") if isinstance(body, str) else body,
        headers=headers,
        method=method,
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout_seconds)
    except urllib.error.HTTPError as e:
        resp = e
    return handler({"response": resp})


class HttpResponse:
    def __init__(self, status: int, headers: dict, body: bytes):
        self.status = status
        self.status_text = ""
        self.headers = headers
        self._body = body
        self._read_pos = 0

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            data = self._body[self._read_pos:]
            self._read_pos = len(self._body)
            return data
        data = self._body[self._read_pos:self._read_pos + size]
        self._read_pos += len(data)
        return data

    def json(self) -> Any:
        return _json.loads(self._body.decode("utf-8", errors="replace"))


def make_response(status: int, body: bytes, headers: Optional[dict] = None) -> HttpResponse:
    return HttpResponse(status, headers or {}, body)
