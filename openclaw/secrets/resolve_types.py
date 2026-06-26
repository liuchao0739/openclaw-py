"""Shared per-runtime cache for resolved SecretRefs and file provider payloads.

Mirrors src/secrets/resolve-types.ts.
"""

from __future__ import annotations

from typing import Any, TypedDict


class SecretRefResolveCache(TypedDict, total=False):
    """Per-runtime cache for resolved SecretRefs and file provider payloads."""

    resolvedByRefKey: dict[str, Any]
    filePayloadByProvider: dict[str, Any]
