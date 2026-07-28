from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .embeddings import EmbeddingProvider, create_noop_embedding_provider


class LocalEmbeddingWorkerClient:
    def __init__(self, script_path: str):
        self._script_path = script_path
        self._child: Optional[Any] = None
        self._next_request_id = 1
        self._pending: Dict[int, Dict[str, Any]] = {}

    def initialize(self, options: Dict[str, Any]) -> None:
        self._send({"type": "initialize", "options": options})

    def embed_query(self, options: Dict[str, Any], text: str) -> List[float]:
        result = self._send({"type": "embedQuery", "options": options, "text": text})
        if isinstance(result, list):
            return [float(v) for v in result]
        return []

    def embed_batch(self, options: Dict[str, Any], texts: List[str]) -> List[List[float]]:
        result = self._send({"type": "embedBatch", "options": options, "texts": texts})
        if isinstance(result, list):
            return [[float(v) for v in entry] for entry in result]
        return []

    def close(self) -> None:
        self._shutdown_child()

    def _send(self, request: Dict[str, Any]) -> Any:
        import subprocess
        import sys

        if self._child is None:
            self._child = subprocess.Popen(
                [sys.executable, self._script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        request_id = self._next_request_id
        self._next_request_id += 1
        payload = {**request, "id": request_id}

        try:
            self._child.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
            self._child.stdin.flush()
            line = self._child.stdout.readline().decode("utf-8").strip()
            if not line:
                raise RuntimeError("Local embedding worker produced no output")
            response = json.loads(line)
            if response.get("ok"):
                return response.get("value")
            error = response.get("error", "Unknown error")
            raise RuntimeError(f"Local embedding worker error: {error}")
        except (BrokenPipeError, OSError) as e:
            self._child = None
            raise RuntimeError(f"Local embedding worker IPC failed: {e}")

    def _shutdown_child(self) -> None:
        if self._child:
            try:
                self._child.kill()
            except Exception:
                pass
            self._child = None


def create_local_embedding_worker_provider(
    options: Dict[str, Any],
    runtime_options: Optional[Dict[str, Any]] = None,
) -> EmbeddingProvider:
    model_path = (options.get("local") or {}).get("modelPath", "") or "local-model"
    worker_options = {
        "config": {},
        "provider": "local",
        "model": options.get("model"),
        "fallback": "none",
        "outputDimensionality": options.get("outputDimensionality"),
        "local": options.get("local", {}),
    }
    script_path = (runtime_options or {}).get("workerScriptPath", "") or os.path.join(
        os.path.dirname(__file__), "embeddings_worker_child.py"
    )
    client = LocalEmbeddingWorkerClient(script_path)
    client.initialize(worker_options)

    provider = create_noop_embedding_provider()
    provider.id = "local"
    provider.model = model_path

    original_fetch = provider.fetch

    def fetch(text: str, session_key: str, opts: Optional[Dict[str, Any]] = None) -> List[float]:
        return client.embed_query(worker_options, text)

    def fetch_batch(inputs: List[Dict[str, Any]], opts: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        texts = [inp.get("text", "") for inp in inputs]
        vectors = client.embed_batch(worker_options, texts)
        results = []
        for i, inp in enumerate(inputs):
            results.append({
                "text": inp.get("text", ""),
                "embedding": vectors[i] if i < len(vectors) else [],
                "dimensions": len(vectors[i]) if i < len(vectors) else 0,
            })
        return results

    provider.fetch = fetch
    provider.fetch_batch = fetch_batch
    provider.close = client.close

    return provider
