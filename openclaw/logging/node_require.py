"""Resolves createRequire from process.getBuiltinModule without static CommonJS imports.

Mirrors src/logging/node-require.ts.
"""

from __future__ import annotations

from typing import Any


def resolve_node_require_from_meta(meta_url: str) -> Any | None:
    import importlib
    try:
        return importlib.import_module
    except Exception:
        return None


__all__ = ["resolve_node_require_from_meta"]
