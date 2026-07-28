from __future__ import annotations

from typing import Any, Dict, List, Optional

CHARS_PER_TOKEN_ESTIMATE = 4


def estimate_tokens_from_file(file_path: str) -> int:
    try:
        with open(file_path, "r") as f:
            content = f.read()
        return len(content) // CHARS_PER_TOKEN_ESTIMATE
    except Exception:
        return 0


def estimate_tokens_for_file_message(message: Dict[str, Any]) -> int:
    content = message.get("content", "")
    return len(str(content)) // CHARS_PER_TOKEN_ESTIMATE


def estimate_session_tokens(
    messages: List[Dict[str, Any]],
    system_prompt: str = "",
    config: Optional[dict] = None,
    tool_results_delta: int = 0,
) -> int:
    total = len(system_prompt)
    for msg in messages:
        content = msg.get("content", "")
        total += len(str(content))
        attachments = msg.get("attachments", [])
        if isinstance(attachments, list):
            for att in attachments:
                total += len(str(att.get("content", "")))
        tool_calls = msg.get("toolCalls", [])
        if isinstance(tool_calls, list):
            total += len(str(tool_calls))
    total += tool_results_delta
    return total // CHARS_PER_TOKEN_ESTIMATE
