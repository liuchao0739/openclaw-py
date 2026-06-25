"""Interactive outbound presentation builder."""

from __future__ import annotations

from typing import Any


def build_interactive_presentation(
    text: str,
    *,
    buttons: list[dict[str, Any]] | None = None,
    selects: list[dict[str, Any]] | None = None,
    context_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build an interactive presentation payload."""
    presentation: dict[str, Any] = {
        "type": "presentation",
        "blocks": [],
    }

    if context_blocks:
        presentation["blocks"].extend(context_blocks)

    text_block = {"type": "text", "text": text}
    presentation["blocks"].append(text_block)

    if buttons:
        presentation["blocks"].append({
            "type": "actions",
            "buttons": buttons,
        })

    if selects:
        for select in selects:
            presentation["blocks"].append({
                "type": "select",
                **select,
            })

    return presentation


def is_interactive_presentation(payload: dict[str, Any]) -> bool:
    """Check if a payload is an interactive presentation."""
    return isinstance(payload, dict) and payload.get("type") == "presentation"
