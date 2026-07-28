from __future__ import annotations

import json
import time
from typing import Any, Callable, Optional

from .error_utils import format_error_message


def _resolve_safe_timeout_delay_ms(value: float, opts: Optional[dict] = None) -> float:
    min_ms = (opts or {}).get("minMs", 0)
    return max(value, min_ms)


def post_json_with_retry(
    url: str,
    data: Any,
    headers: Optional[dict] = None,
    max_retries: int = 3,
    initial_delay_ms: float = 300,
    timeout_ms: float = 30_000,
) -> dict:
    import urllib.request
    import urllib.error

    last_error = None
    for attempt in range(max_retries):
        try:
            req_data = json.dumps(data).encode("utf-8")
            req_headers = {"Content-Type": "application/json"}
            if headers:
                req_headers.update(headers)

            req = urllib.request.Request(url, data=req_data, headers=req_headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout_ms / 1000.0) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except Exception as err:
            last_error = err
            if attempt >= max_retries - 1:
                break
            delay = _resolve_safe_timeout_delay_ms(
                initial_delay_ms * (2**attempt),
                {"minMs": 0},
            )
            time.sleep(delay / 1000.0)

    raise Exception(f"POST {url} failed: {format_error_message(last_error)}")
