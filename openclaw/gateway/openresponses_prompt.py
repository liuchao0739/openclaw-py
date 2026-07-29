"""Prompt adapter from OpenAI Responses input items to OpenClaw agent messages.

Mirrors src/gateway/openresponses-prompt.ts.
"""

from __future__ import annotations

from typing import Any

def build_agent_prompt(*args: Any, **kwargs: Any) -> Any: ...
