from __future__ import annotations

from typing import Any

from .cli_constants import (
    CLAUDE_CLI_BACKEND_ID,
    CLAUDE_CLI_DEFAULT_ALLOWLIST_REFS,
)

_CLAUDE_CLI_DEFAULT_CONTEXT_WINDOW = 200_000

_CLAUDE_CLI_MODEL_LABELS: dict[str, str] = {
    "claude-opus-4-8": "Claude Opus 4.8 (Claude CLI)",
    "claude-opus-4-7": "Claude Opus 4.7 (Claude CLI)",
    "claude-opus-4-6": "Claude Opus 4.6 (Claude CLI)",
    "claude-sonnet-4-6": "Claude Sonnet 4.6 (Claude CLI)",
}


def _resolve_claude_cli_image_media_input(
    model_id: str,
) -> dict[str, Any]:
    max_side_px = 2576 if model_id in ("claude-opus-4-8", "claude-opus-4-7") else 1568
    return {
        "image": {
            "maxSidePx": max_side_px,
            "preferredSidePx": max_side_px,
            "tokenMode": "provider",
        },
    }


def _extract_claude_cli_model_ids() -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for ref in CLAUDE_CLI_DEFAULT_ALLOWLIST_REFS:
        if not ref.startswith(f"{CLAUDE_CLI_BACKEND_ID}/"):
            continue
        model_id = ref[len(CLAUDE_CLI_BACKEND_ID) + 1:]
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        ids.append(model_id)
    return ids


def build_claude_cli_catalog_entries() -> list[dict[str, Any]]:
    return [
        {
            "id": model_id,
            "name": _CLAUDE_CLI_MODEL_LABELS.get(model_id, f"{model_id} (Claude CLI)"),
            "provider": CLAUDE_CLI_BACKEND_ID,
            "reasoning": True,
            "input": ["text", "image"],
            "mediaInput": _resolve_claude_cli_image_media_input(model_id),
            "contextWindow": 1_048_576 if model_id == "claude-opus-4-8" else _CLAUDE_CLI_DEFAULT_CONTEXT_WINDOW,
        }
        for model_id in _extract_claude_cli_model_ids()
    ]