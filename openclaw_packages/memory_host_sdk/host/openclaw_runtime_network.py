from __future__ import annotations

from typing import Any, Dict, Optional


def fetch_with_ssr_guard(url: str, headers: Optional[Dict[str, str]] = None, timeout_ms: int = 30000) -> Dict[str, Any]:
    from .remote_http import http_get
    return http_get(url, headers, timeout_ms)


def should_use_env_http_proxy_for_url(url: str) -> bool:
    return False


def ssrf_policy_from_http_base_url_allowed_hostname(base_url: str) -> Dict[str, Any]:
    return {
        "allowPrivateNetwork": False,
        "dangerouslyAllowPrivateNetwork": False,
        "allowRfc2544BenchmarkRange": False,
        "allowIpv6UniqueLocalRange": False,
        "allowedHostnames": [],
        "hostnameAllowlist": [],
    }
