from __future__ import annotations

from typing import Any, Dict, List, Optional

from .batch_provider_common import normalize_batch_embeddings_options


class EmbeddingProviderNodeLlama:
    def __init__(self, options: Dict[str, Any]):
        self._options = options
        self._model_path = options.get("modelPath", "")
        self._model_name = options.get("modelName", "")
        self._dimensions = options.get("dimensions", 768)
        self._chunk_size = options.get("chunkSize", 512)

    def fetch(self, text: str, session_key: str, opts: Optional[Dict[str, Any]] = None) -> List[float]:
        raise RuntimeError("node-llama embeddings require the llama-cpp-python runtime")

    def fetch_batch(
        self,
        inputs: List[Dict[str, Any]],
        opts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise RuntimeError("node-llama embeddings require the llama-cpp-python runtime")


def create_embedding_provider_node_llama(options: Dict[str, Any]) -> EmbeddingProviderNodeLlama:
    return EmbeddingProviderNodeLlama(options)
