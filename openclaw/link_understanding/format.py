"""Link-understanding formatter appends normalized fetched-link summaries to the
agent-visible message body.

Mirrors src/link-understanding/format.ts.
"""

from __future__ import annotations

from typing import Iterable


def _normalize_string_entries(outputs: Iterable) -> list[str]:
    """Filter and trim string entries, dropping empty values."""
    result: list[str] = []
    for item in outputs:
        if isinstance(item, str):
            trimmed = item.strip()
            if trimmed:
                result.append(trimmed)
    return result


def format_link_understanding_body(params: dict) -> str:
    """Append normalized link-understanding outputs to the agent-visible body."""
    outputs = _normalize_string_entries(params.get("outputs", []))
    if not outputs:
        return params.get("body") or ""

    base = (params.get("body") or "").strip()
    if not base:
        return "\n".join(outputs)
    return f"{base}\n\n" + "\n".join(outputs)
