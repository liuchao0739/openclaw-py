from __future__ import annotations

from typing import Any

from openclaw.config.models import OpenClawConfig


class ConfigValidationIssue:
    def __init__(
        self,
        path: str,
        message: str,
        allowed_values: list[Any] | None = None,
        allowed_values_hidden_count: int = 0,
    ):
        self.path = path
        self.message = message
        self.allowed_values = allowed_values
        self.allowed_values_hidden_count = allowed_values_hidden_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "message": self.message,
            "allowedValues": self.allowed_values,
            "allowedValuesHiddenCount": self.allowed_values_hidden_count,
        }


def _format_config_path(segments: list[Any]) -> str:
    return ".".join(str(s) for s in segments)


def _summarize_allowed_values(values: list[Any]) -> dict[str, Any]:
    if not values:
        return {"values": [], "hiddenCount": 0}
    visible = values[:8]
    hidden = len(values) - len(visible)
    return {"values": visible, "hiddenCount": hidden}


def validate_config_object_raw(
    raw: Any,
    opts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"ok": False, "issues": [{"path": "<root>", "message": "Config must be an object"}]}
    try:
        config = OpenClawConfig.model_validate(raw)
        return {"ok": True, "config": config}
    except Exception as e:
        issues = [{"path": "<root>", "message": str(e)}]
        return {"ok": False, "issues": issues}


def validate_config_object(
    raw: Any,
    opts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return validate_config_object_raw(raw, opts)


def validate_config_object_with_plugins(
    raw: Any,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return validate_config_object_raw(raw, params)


def validate_config_object_raw_with_plugins(
    raw: Any,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return validate_config_object_raw(raw, params)
