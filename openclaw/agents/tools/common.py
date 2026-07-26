"""Shared built-in tool contracts and helpers.

Defines erased tool types, parameter readers, JSON results, progress blocks, and media sanitization.
"""

from __future__ import annotations

from typing import Any


class ToolInputError(Exception):
    """Error for invalid tool input parameters."""

    status = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.name = "ToolInputError"


class ToolAuthorizationError(ToolInputError):
    """Error for tool authorization failures."""

    status = 403

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.name = "ToolAuthorizationError"


def as_tool_params_record(params: Any) -> dict[str, Any]:
    """Cast params to a record dict, returning empty dict for non-objects."""
    if params and isinstance(params, dict):
        return params
    return {}


def _read_param_raw(params: dict[str, Any], key: str) -> Any:
    """Read a param value, supporting snake_case fallback."""
    if key in params:
        return params[key]
    # Try snake_case conversion of camelCase key
    snake_key = "".join(("_" + c.lower()) if c.isupper() else c for c in key)
    return params.get(snake_key)


def read_string_param(
    params: dict[str, Any],
    key: str,
    *,
    required: bool = False,
    trim: bool = True,
    label: str | None = None,
    allow_empty: bool = False,
) -> str | None:
    """Read a string parameter from a params dict."""
    label = label or key
    raw = _read_param_raw(params, key)
    if not isinstance(raw, str):
        if required:
            raise ToolInputError(f"{label} required")
        return None
    value = raw.strip() if trim else raw
    if not value and not allow_empty:
        if required:
            raise ToolInputError(f"{label} required")
        return None
    return value


def read_optional_string_param(
    params: dict[str, Any],
    key: str,
    *,
    trim: bool = True,
) -> str | None:
    """Read an optional string parameter."""
    raw = _read_param_raw(params, key)
    if not isinstance(raw, str):
        return None
    value = raw.strip() if trim else raw
    return value or None


def read_number_param(
    params: dict[str, Any],
    key: str,
    *,
    required: bool = False,
    label: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
) -> int | None:
    """Read a number parameter from a params dict."""
    label = label or key
    raw = _read_param_raw(params, key)
    if raw is None:
        if required:
            raise ToolInputError(f"{label} required")
        return None
    try:
        value = int(raw)
    except (ValueError, TypeError):
        try:
            value = int(float(raw))
        except (ValueError, TypeError):
            if required:
                raise ToolInputError(f"{label} must be a number")
            return None
    if min_value is not None and value < min_value:
        raise ToolInputError(f"{label} must be >= {min_value}")
    if max_value is not None and value > max_value:
        raise ToolInputError(f"{label} must be <= {max_value}")
    return value


def read_positive_integer_param(
    params: dict[str, Any],
    key: str,
    *,
    max_value: int | None = None,
    message: str | None = None,
) -> int | None:
    """Read a positive integer parameter, rejecting invalid or out-of-range values."""
    raw = _read_param_raw(params, key)
    value: int | None = None
    if isinstance(raw, bool):
        value = None
    elif isinstance(raw, int) and raw > 0:
        value = raw
    elif isinstance(raw, float) and raw > 0 and raw == int(raw):
        value = int(raw)
    elif isinstance(raw, str):
        trimmed = raw.strip()
        if trimmed:
            try:
                parsed = float(trimmed)
            except ValueError:
                parsed = float("nan")
            if parsed == int(parsed) and parsed > 0:
                value = int(parsed)

    if value is None and raw is not None:
        raise ToolInputError(message or f"{key} must be a positive integer")
    if value is not None and max_value is not None and value > max_value:
        raise ToolInputError(message or f"{key} must be a positive integer")
    return value


def read_boolean_param(
    params: dict[str, Any],
    key: str,
    *,
    default: bool = False,
) -> bool:
    """Read a boolean parameter with a default."""
    raw = _read_param_raw(params, key)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in ("true", "1", "yes", "on")
    if isinstance(raw, (int, float)):
        return bool(raw)
    return default


def read_array_param(
    params: dict[str, Any],
    key: str,
) -> list[Any]:
    """Read an array parameter."""
    raw = _read_param_raw(params, key)
    if isinstance(raw, list):
        return raw
    return []


def create_action_gate(actions: dict[str, bool] | None) -> Any:
    """Create a gate function that checks action permissions."""

    def gate(key: str, default_value: bool = True) -> bool:
        if actions is None:
            return default_value
        value = actions.get(key)
        if value is None:
            return default_value
        return value is not False

    return gate


def json_text_result(text: str) -> dict[str, Any]:
    """Create a text-only tool result."""
    return {
        "content": [{"type": "text", "text": text}],
    }


def json_error_result(message: str) -> dict[str, Any]:
    """Create an error tool result."""
    return {
        "content": [{"type": "text", "text": f"Error: {message}"}],
        "isError": True,
    }
