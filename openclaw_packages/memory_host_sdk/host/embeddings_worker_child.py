from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional


class _NoopProvider:
    def __init__(self, options: Dict[str, Any]):
        self._options = options
        self._model_path = (options.get("local") or {}).get("modelPath", "")

    def fetch(self, text: str, session_key: str = "") -> List[float]:
        return [0.0] * 768

    def fetch_batch(self, inputs: List[Dict[str, Any]], opts: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        results = []
        for inp in inputs:
            results.append({
                "text": inp.get("text", ""),
                "embedding": [0.0] * 768,
                "dimensions": 768,
            })
        return results

    def close(self) -> None:
        pass


_provider: Optional[_NoopProvider] = None
_provider_options_key: Optional[str] = None


def _get_provider(options: Dict[str, Any]) -> _NoopProvider:
    global _provider, _provider_options_key
    key = json.dumps(options, sort_keys=True)
    if _provider and _provider_options_key == key:
        return _provider
    if _provider:
        _provider.close()
    _provider = _NoopProvider(options)
    _provider_options_key = key
    return _provider


def _close_provider() -> None:
    global _provider, _provider_options_key
    if _provider:
        _provider.close()
    _provider = None
    _provider_options_key = None


def _serialize_error(err: Exception) -> Dict[str, Any]:
    result = {"message": str(err)}
    if hasattr(err, "code") and isinstance(err.code, str):
        result["code"] = err.code
    return result


def _handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    req_type = request.get("type")
    req_id = request.get("id", 0)

    if req_type == "close":
        _close_provider()
        return {"id": req_id, "ok": True}

    options = request.get("options", {})
    provider = _get_provider(options)

    if req_type == "initialize":
        return {"id": req_id, "ok": True}

    if req_type == "embedQuery":
        text = request.get("text", "")
        value = provider.fetch(text)
        return {"id": req_id, "ok": True, "value": value}

    if req_type == "embedBatch":
        texts = request.get("texts", [])
        inputs = [{"text": t} for t in texts]
        value = provider.fetch_batch(inputs)
        vectors = [v["embedding"] for v in value]
        return {"id": req_id, "ok": True, "value": vectors}

    return {"id": req_id, "ok": False, "error": {"message": f"Unknown request type: {req_type}"}}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = _handle_request(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"id": 0, "ok": False, "error": _serialize_error(e)}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
