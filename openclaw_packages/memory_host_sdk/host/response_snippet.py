from __future__ import annotations

from typing import Any, Dict, List, Optional


def format_response_snippet(content: str, max_chars: int = 200) -> str:
    text = str(content or "")
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def parse_response_snippet(snippet: str) -> Dict[str, Any]:
    return {"content": snippet, "timestamp": 0}


def truncate_for_display(text: str, max_chars: int = 120) -> str:
    text = str(text or "")
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + "…"
