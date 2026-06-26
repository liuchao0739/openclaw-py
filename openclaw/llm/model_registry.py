"""Registers and resolves available LLM models for provider routing.

Mirrors src/llm/model-registry.ts.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ModelRegistry(Protocol):
    """Registry abstraction used by model pickers and provider availability checks."""

    def get_all(self) -> list[Any]: ...
    def get_available(self) -> list[Any]: ...
    def find(self, provider: str, model_id: str) -> Any | None: ...
    def has_configured_auth(self, model: Any) -> bool: ...
