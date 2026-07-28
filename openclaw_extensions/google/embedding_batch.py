import os
import json
import time
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field

from .config_defaults import GoogleConfigDefaults
from .embedding_provider import GoogleEmbeddingProvider, GoogleEmbeddingResponse


@dataclass
class EmbeddingBatchItem:
    text: str
    metadata: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None
    error: Optional[str] = None


@dataclass
class EmbeddingBatchResult:
    items: List[EmbeddingBatchItem] = field(default_factory=list)
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    batch_index: int = 0
    total_batches: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [
                {
                    "text": item.text,
                    "metadata": item.metadata,
                    "embedding": item.embedding,
                    "error": item.error,
                }
                for item in self.items
            ],
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "batch_index": self.batch_index,
            "total_batches": self.total_batches,
        }


class EmbeddingBatchProcessor:
    def __init__(
        self,
        provider: Optional[GoogleEmbeddingProvider] = None,
        config: Optional[GoogleConfigDefaults] = None,
        batch_size: int = 250,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ):
        self.provider = provider or GoogleEmbeddingProvider(config=config)
        self.config = config
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.progress_callback = progress_callback

    def process_batch(
        self,
        items: List[EmbeddingBatchItem],
        task_type: Optional[str] = None,
    ) -> EmbeddingBatchResult:
        result = EmbeddingBatchResult(
            items=items,
            total=len(items),
        )

        texts = [item.text for item in items]
        embeddings = self._embed_with_retry(texts, task_type)

        for i, item in enumerate(items):
            if embeddings[i] is not None:
                item.embedding = embeddings[i]
                result.succeeded += 1
            else:
                item.error = "Failed to generate embedding"
                result.failed += 1

        return result

    def process_all(
        self,
        texts: List[str],
        metadata_list: Optional[List[Dict[str, Any]]] = None,
        task_type: Optional[str] = None,
    ) -> EmbeddingBatchResult:
        items = []
        for i, text in enumerate(texts):
            metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else None
            items.append(EmbeddingBatchItem(text=text, metadata=metadata))

        total_batches = max(1, (len(items) + self.batch_size - 1) // self.batch_size)
        all_results: List[EmbeddingBatchItem] = []

        for batch_idx in range(total_batches):
            start = batch_idx * self.batch_size
            end = min(start + self.batch_size, len(items))
            batch_items = items[start:end]

            batch_result = self.process_batch(batch_items, task_type)
            batch_result.batch_index = batch_idx
            batch_result.total_batches = total_batches

            all_results.extend(batch_result.items)

            if self.progress_callback:
                self.progress_callback(batch_idx + 1, total_batches, len(batch_items))

        result = EmbeddingBatchResult(
            items=all_results,
            total=len(items),
            succeeded=sum(1 for item in all_results if item.embedding is not None),
            failed=sum(1 for item in all_results if item.embedding is None),
        )
        return result

    def _embed_with_retry(
        self,
        texts: List[str],
        task_type: Optional[str] = None,
    ) -> List[Optional[List[float]]]:
        last_error = None
        for attempt in range(self.max_retries):
            try:
                responses = self.provider.embed_batch(texts, task_type)
                return [resp.embedding for resp in responses]
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        return [None] * len(texts)