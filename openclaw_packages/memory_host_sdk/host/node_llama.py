from __future__ import annotations

from typing import Any, Dict, List, Optional


class NodeLlamaBinding:
    def __init__(self, model_path: Optional[str] = None, options: Optional[Dict[str, Any]] = None):
        self._model_path = model_path or ""
        self._options = options or {}

    def is_available(self) -> bool:
        return False

    def load_model(self, model_path: str) -> None:
        self._model_path = model_path

    def create_embedding(self, text: str, chunk_size: int = 512) -> List[float]:
        raise RuntimeError("node-llama native binding is not available in this Python runtime")


def create_node_llama_binding(model_path: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> NodeLlamaBinding:
    return NodeLlamaBinding(model_path, options)


def is_node_llama_available() -> bool:
    return False
