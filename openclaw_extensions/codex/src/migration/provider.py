"""Codex migration provider."""

from __future__ import annotations

from typing import Any


def build_codex_migration_provider(_params: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": "codex",
        "label": "Codex",
        "description": (
            "Inventory and promote Codex CLI skills while keeping Codex native plugins and hooks explicit."
        ),
    }
