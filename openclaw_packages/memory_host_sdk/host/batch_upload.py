from __future__ import annotations

import json
import os
import time
from typing import Any, List, Optional

from .batch_http import post_json_with_retry
from .batch_utils import normalize_batch_base_url


def _resolve_safe_timeout_delay_ms(value: float, opts: Optional[dict] = None) -> float:
    min_ms = (opts or {}).get("minMs", 0)
    return max(value, min_ms)


def upload_batch_jsonl_file(
    base_url: str,
    api_key: str,
    batch_file_path: str,
    provider_id: str,
    model: str,
    poll_interval_ms: float = 2000,
    timeout_ms: float = 600_000,
    extra_headers: Optional[dict] = None,
) -> dict:
    url = normalize_batch_base_url(base_url) + "/batches"

    with open(batch_file_path, "r") as f:
        lines = f.readlines()

    requests = []
    for line in lines:
        if line.strip():
            entry = json.loads(line)
            requests.append({
                "custom_id": entry.get("custom_id", ""),
                "model": model,
                "input": entry.get("input", {}),
            })

    data = {
        "input": requests,
        "model": model,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    start_time = time.time()
    response = post_json_with_retry(url, data, headers)
    batch_id = response.get("id", "")

    if not batch_id:
        raise Exception(f"Failed to create batch: {response}")

    elapsed = 0
    while elapsed < timeout_ms:
        elapsed_ms = (time.time() - start_time) * 1000
        status_url = f"{normalize_batch_base_url(base_url)}/batches/{batch_id}"
        try:
            status_resp = post_json_with_retry(
                status_url,
                {},
                headers,
                max_retries=2,
            )
            status = status_resp.get("status", "")
            if status in ("completed", "failed", "cancelled", "expired"):
                return status_resp
        except Exception:
            pass

        delay = _resolve_safe_timeout_delay_ms(poll_interval_ms, {"minMs": 100})
        time.sleep(delay / 1000.0)
        elapsed = (time.time() - start_time) * 1000

    raise TimeoutError(f"Batch {batch_id} timed out after {timeout_ms}ms")
