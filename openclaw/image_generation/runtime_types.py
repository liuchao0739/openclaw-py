"""Public runtime parameter and result types for image generation calls.

Mirrors src/image-generation/runtime-types.ts. TypedDict stubs — the full
type hierarchy depends on many unported modules.
"""

from __future__ import annotations

from typing import Any, TypedDict


class GenerateImageParams(TypedDict, total=False):
    cfg: dict[str, Any]
    prompt: str
    agentDir: str
    modelOverride: str
    count: int
    size: str
    aspectRatio: str
    resolution: str
    quality: str
    outputFormat: str
    background: str
    inputImages: list[dict[str, Any]]
    autoProviderFallback: bool
    timeoutMs: int
    providerOptions: dict[str, Any]
    ssrfPolicy: Any


class GenerateImageRuntimeResult(TypedDict, total=False):
    images: list[dict[str, Any]]
    provider: str
    model: str
    attempts: list[dict[str, Any]]
    normalization: dict[str, Any]
    metadata: dict[str, Any]
    ignoredOverrides: list[dict[str, Any]]
