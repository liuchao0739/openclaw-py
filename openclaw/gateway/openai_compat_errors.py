"""OpenAI-compatible error helpers.

Mirrors src/gateway/openai-compat-errors.ts.
"""

from __future__ import annotations

from typing import Any

OpenAiCompatError = Any

def resolve_open_ai_compat_error(*args: Any, **kwargs: Any) -> Any: ...
def validate_open_ai_sampling_params(*args: Any, **kwargs: Any) -> Any: ...
