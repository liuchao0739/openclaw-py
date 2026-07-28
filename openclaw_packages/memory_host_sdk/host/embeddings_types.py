from __future__ import annotations

from typing import Any, List, Optional


DEFAULT_LOCAL_MODEL = "hf:ggml-org/embeddinggemma-300m-qat-q8_0-GGUF/embeddinggemma-300m-qat-Q8_0.gguf"


class EmbeddingProvider:
    def __init__(self, id: str, model: str):
        self.id = id
        self.model = model
        self.max_input_tokens: Optional[int] = None

    async def embed_query(self, text: str, options: Optional[dict] = None) -> List[float]:
        raise NotImplementedError

    async def embed_batch(self, texts: List[str], options: Optional[dict] = None) -> List[List[float]]:
        raise NotImplementedError

    async def embed_batch_inputs(self, inputs: List[dict], options: Optional[dict] = None) -> List[List[float]]:
        raise NotImplementedError

    async def close(self) -> None:
        pass
