from __future__ import annotations

from typing import Any, Dict, Optional

from .remote_http import http_post


def post_json(url: str, data: Any, headers: Optional[Dict[str, str]] = None, timeout_ms: int = 30000) -> Dict[str, Any]:
    return http_post(url, data, headers, timeout_ms)


def post_json_stream(url: str, data: Any, headers: Optional[Dict[str, str]] = None, timeout_ms: int = 30000) -> Dict[str, Any]:
    return http_post(url, data, headers, timeout_ms)
