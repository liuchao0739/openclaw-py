from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional


def http_get(url: str, headers: Optional[Dict[str, str]] = None, timeout_ms: int = 30000) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout_ms / 1000) as resp:
            body = resp.read().decode("utf-8")
            return {"ok": True, "status": resp.status, "body": json.loads(body) if body else {}}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "body": {}}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


def http_post(url: str, data: Any, headers: Optional[Dict[str, str]] = None, timeout_ms: int = 30000) -> Dict[str, Any]:
    body = json.dumps(data).encode("utf-8") if data is not None else b""
    hdrs = headers or {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout_ms / 1000) as resp:
            resp_body = resp.read().decode("utf-8")
            return {"ok": True, "status": resp.status, "body": json.loads(resp_body) if resp_body else {}}
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            pass
        return {"ok": False, "status": e.code, "body": json.loads(err_body) if err_body else {}}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


class RemoteHttpClient:
    def __init__(self, base_url: str, headers: Optional[Dict[str, str]] = None, timeout_ms: int = 30000):
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}
        self._timeout_ms = timeout_ms

    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        hdrs = dict(self._headers)
        if headers:
            hdrs.update(headers)
        return http_get(self._base_url + path, hdrs, self._timeout_ms)

    def post(self, path: str, data: Any, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        hdrs = dict(self._headers)
        if headers:
            hdrs.update(headers)
        return http_post(self._base_url + path, data, hdrs, self._timeout_ms)
