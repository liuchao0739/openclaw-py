from typing import Optional, Dict, Any, List

from .config_defaults import GoogleConfigDefaults
from .embedding_provider import GoogleEmbeddingProvider, GoogleEmbeddingResponse


class MemoryEmbeddingAdapter:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._provider = GoogleEmbeddingProvider(config=config)

    def initialize(self) -> None:
        self._provider.initialize()

    def embed(self, text: str) -> List[float]:
        response = self._provider.embed(text)
        return response.embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        responses = self._provider.embed_batch(texts)
        return [resp.embedding for resp in responses]

    def get_embedding_dimension(self) -> int:
        test_embedding = self.embed("test")
        return len(test_embedding)

    def to_memory_format(self, embedding: List[float]) -> Dict[str, Any]:
        return {
            "embedding": embedding,
            "dimension": len(embedding),
            "model": self._provider.get_model(),
            "provider": "google",
        }

    def from_memory_format(self, data: Dict[str, Any]) -> List[float]:
        return data.get("embedding", [])

    def validate_embedding(self, embedding: List[float], expected_dimension: Optional[int] = None) -> bool:
        if not embedding:
            return False
        if expected_dimension and len(embedding) != expected_dimension:
            return False
        return True

    def compute_similarity(
        self,
        embedding_a: List[float],
        embedding_b: List[float],
    ) -> float:
        if len(embedding_a) != len(embedding_b):
            return 0.0
        dot_product = sum(a * b for a, b in zip(embedding_a, embedding_b))
        magnitude_a = sum(a * a for a in embedding_a) ** 0.5
        magnitude_b = sum(b * b for b in embedding_b) ** 0.5
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        return dot_product / (magnitude_a * magnitude_b)


def create_memory_embedding_adapter(config: Optional[GoogleConfigDefaults] = None) -> MemoryEmbeddingAdapter:
    return MemoryEmbeddingAdapter(config=config)