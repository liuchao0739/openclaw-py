from __future__ import annotations

import os
from typing import Any


def _get_model_match_candidates(model_id: str, model_name: str | None = None) -> list[str]:
    values = [model_id, model_name] if model_name else [model_id]
    result: list[str] = []
    for value in values:
        lower = value.lower()
        result.append(lower)
        result.append(lower.replace(" ", "-").replace("_", "-").replace(".", "-").replace(":", "-"))
    return result


def supports_bedrock_prompt_caching(model_id: str, model_name: str | None = None) -> bool:
    candidates = _get_model_match_candidates(model_id, model_name)
    has_claude_ref = any("claude" in s for s in candidates)
    if not has_claude_ref:
        if os.environ.get("AWS_BEDROCK_FORCE_CACHE") == "1":
            return True
        return False
    if any("-4-" in s for s in candidates):
        return True
    if any("claude-fable-5" in s for s in candidates):
        return True
    if any("claude-3-7-sonnet" in s for s in candidates):
        return True
    if any("claude-3-5-haiku" in s for s in candidates):
        return True
    return False


__all__ = ["supports_bedrock_prompt_caching"]