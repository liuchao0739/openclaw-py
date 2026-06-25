"""Model tool support helpers.

Checks whether a model supports specific tool features (function calling, parallel calls, etc.).
"""

from __future__ import annotations

from typing import Any


def supports_function_calling(model: dict[str, Any] | None) -> bool:
    """Check if a model supports function/tool calling."""
    if not model:
        return True  # Assume supported by default
    return model.get("toolCallCapable", True) is not False


def supports_parallel_tool_calls(model: dict[str, Any] | None) -> bool:
    """Check if a model supports parallel tool calls."""
    if not model:
        return True
    return model.get("parallelToolCallCapable", True) is not False


def supports_vision(model: dict[str, Any] | None) -> bool:
    """Check if a model supports vision/image input."""
    if not model:
        return False
    input_types = model.get("input", [])
    return "image" in input_types if isinstance(input_types, list) else False


def supports_streaming(model: dict[str, Any] | None) -> bool:
    """Check if a model supports streaming responses."""
    if not model:
        return True
    return model.get("streamingCapable", True) is not False
