from __future__ import annotations

from typing import Any


def build_content_block(
    block_type: str,
    content: Any = None,
    **metadata: Any,
) -> dict[str, Any]:
    return {
        "type": block_type,
        "content": content,
        "metadata": metadata,
    }


def parse_content_blocks(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [b for b in raw if isinstance(b, dict)]
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, str):
        return [{"type": "text", "content": raw}]
    return []
