"""Capability runtime vitest shims package.

Mirrors src/plugins/capability-runtime-vitest-shims/. These are test-only
stubs for capability runtime modules. Stub implementations provided.
"""

from __future__ import annotations

from typing import Any


def create_media_runtime_shim() -> dict[str, Any]:
    """Create a media runtime shim for tests."""
    return {
        "supported": False,
        "providers": [],
    }


def create_config_runtime_shim() -> dict[str, Any]:
    """Create a config runtime shim for tests."""
    return {
        "loaded": False,
        "config": {},
    }


def create_speech_core_shim() -> dict[str, Any]:
    """Create a speech core shim for tests."""
    return {
        "available": False,
        "engines": [],
    }
