from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


def _as_record(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return value
    return None


def _malformed_embedding_response(error_prefix: str) -> Exception:
    return RuntimeError(f"{error_prefix}: malformed JSON response")


def _read_embedding_vector(value: Any, error_prefix: str) -> List[float]:
    if not isinstance(value, list):
        raise _malformed_embedding_response(error_prefix)
    for entry in value:
        if not isinstance(entry, (int, float)) or not isinstance(entry, (int, float)):
            raise _malformed_embedding_response(error_prefix)
        if isinstance(entry, float) and not (entry == entry):
            raise _malformed_embedding_response(error_prefix)
    return [float(v) for v in value]


def _resolve_expected_embedding_count(body: Any) -> Optional[int]:
    record = _as_record(body)
    if not record:
        return None
    if isinstance(record.get("input"), list):
        return len(record["input"])
    return None


def fetch_remote_embedding_vectors(
    url: str,
    headers: Dict[str, str],
    body: Any,
    error_prefix: str,
    timeout_ms: int = 30000,
) -> List[List[float]]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_ms / 1000) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError(f"{error_prefix}: HTTP {e.code}: {body_text}")
    except Exception as e:
        raise RuntimeError(f"{error_prefix}: {e}")

    root = _as_record(payload)
    if not root or not isinstance(root.get("data"), list):
        raise _malformed_embedding_response(error_prefix)

    expected_count = _resolve_expected_embedding_count(body)
    if expected_count is not None and len(root["data"]) != expected_count:
        raise _malformed_embedding_response(error_prefix)

    results = []
    for entry in root["data"]:
        record = _as_record(entry)
        if not record:
            raise _malformed_embedding_response(error_prefix)
        results.append(_read_embedding_vector(record.get("embedding"), error_prefix))
    return results
