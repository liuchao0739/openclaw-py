from __future__ import annotations

from typing import Any, Dict, List, Optional

from .batch_provider_common import normalize_batch_embeddings_options


class EmbeddingProviderRemote:
    def __init__(self, options: Dict[str, Any], http_client: Optional[Any] = None):
        self._options = options
        self._http_client = http_client
        self._url = options.get("url", "")
        self._batch_url = options.get("batchUrl", "")
        self._timeout_ms = options.get("timeoutMs", 60000)
        self._api_key = options.get("apiKey", "")

    def fetch(self, text: str, session_key: str, opts: Optional[Dict[str, Any]] = None) -> List[float]:
        import json
        import urllib.request

        if not self._url:
            raise RuntimeError("EmbeddingProviderRemote requires a configured url")

        data = json.dumps({
            "text": text,
            "sessionKey": session_key,
        }).encode("utf-8")

        req = urllib.request.Request(
            self._url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}" if self._api_key else "",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout_ms / 1000) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body.get("embedding", [])
        except Exception as err:
            raise RuntimeError(f"EmbeddingProviderRemote.fetch failed: {err}")

    def fetch_batch(
        self,
        inputs: List[Dict[str, Any]],
        opts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        import json
        import urllib.request

        batch_url = self._batch_url or (self._url + "/batch")

        data = json.dumps({"inputs": inputs}).encode("utf-8")
        req = urllib.request.Request(
            batch_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}" if self._api_key else "",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout_ms / 1000) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body
        except Exception as err:
            raise RuntimeError(f"EmbeddingProviderRemote.fetch_batch failed: {err}")


def create_embedding_provider_remote(options: Dict[str, Any], http_client: Optional[Any] = None) -> EmbeddingProviderRemote:
    return EmbeddingProviderRemote(options, http_client)
