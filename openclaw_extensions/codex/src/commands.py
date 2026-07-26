"""Codex plugin command registration."""

from __future__ import annotations

from typing import Any


def create_codex_command(options: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "name": "codex",
        "description": "Inspect and control the Codex app-server harness",
        "ownership": "reserved",
        "acceptsArgs": True,
        "requireAuth": True,
        "handler": lambda _ctx: {"text": "Codex command handler is not available in this environment."},
    }
