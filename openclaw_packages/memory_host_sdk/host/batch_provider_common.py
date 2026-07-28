from __future__ import annotations

from typing import Any, Dict, List, Optional


def normalize_batch_embeddings_options(options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    opts = options or {}
    return {
        "enabled": opts.get("enabled", True),
        "batchSize": opts.get("batchSize", 32),
        "maxQueueSize": opts.get("maxQueueSize", 256),
        "flushIntervalMs": opts.get("flushIntervalMs", 100),
        "modelPath": opts.get("modelPath", ""),
        "modelName": opts.get("modelName", ""),
        "dimensions": opts.get("dimensions", 768),
        "chunkSize": opts.get("chunkSize", 512),
    }


def merge_batch_embeddings_options(
    defaults: Optional[Dict[str, Any]],
    overrides: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    merged = dict(defaults or {})
    if overrides:
        merged.update(overrides)
    return normalize_batch_embeddings_options(merged)


def create_batch_embeddings_provider(
    provider_type: str,
    options: Dict[str, Any],
    http_client: Optional[Any] = None,
) -> Any:
    if provider_type == "remote":
        from .embeddings_provider_remote import create_embedding_provider_remote
        return create_embedding_provider_remote(options, http_client)
    if provider_type == "node-llama":
        from .embeddings_provider_node_llama import create_embedding_provider_node_llama
        return create_embedding_provider_node_llama(options)
    raise RuntimeError(f"Unknown batch embeddings provider type: {provider_type}")
