"""Interactive payload helpers normalize structured interactive UI payloads.

Mirrors src/interactive/payload.ts. Partial port — types and key normalization
functions are included; complex rendering helpers are deferred.
"""

from __future__ import annotations

import re
from typing import Any, Literal, Mapping, TypedDict

InteractiveButtonStyle = Literal["primary", "secondary", "success", "danger"]
MessagePresentationTone = Literal["info", "success", "warning", "danger", "neutral"]


class MessagePresentationAction(TypedDict, total=False):
    type: str
    command: str
    value: str


class MessagePresentationButton(TypedDict, total=False):
    label: str
    action: MessagePresentationAction
    value: str
    url: str
    webApp: dict[str, str]
    web_app: dict[str, str]
    priority: int
    disabled: bool
    reusable: bool
    style: str


def _normalize_optional_string(value: Any) -> str | None:
    if isinstance(value, str):
        s = value.strip()
        return s or None
    return None


def _normalize_optional_lowercase_string(value: Any) -> str | None:
    if isinstance(value, str):
        s = value.strip().lower()
        return s or None
    return None


def _as_optional_record(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    return None


_VALID_BUTTON_STYLES = frozenset({"primary", "secondary", "success", "danger"})
_VALID_TONES = frozenset({"info", "success", "warning", "danger", "neutral"})


def normalize_button_style(value: Any) -> InteractiveButtonStyle | None:
    """Normalize a button style hint, returning None for invalid values."""
    normalized = _normalize_optional_lowercase_string(value)
    if normalized and normalized in _VALID_BUTTON_STYLES:
        return normalized  # type: ignore
    return None


def normalize_presentation_tone(value: Any) -> MessagePresentationTone | None:
    """Normalize a message presentation tone, returning None for invalid values."""
    normalized = _normalize_optional_lowercase_string(value)
    if normalized and normalized in _VALID_TONES:
        return normalized  # type: ignore
    return None


def normalize_button_label(value: Any) -> str | None:
    """Normalize a button label, returning None for empty/non-string values."""
    return _normalize_optional_string(value)


def normalize_button_action(value: Any) -> MessagePresentationAction | None:
    """Normalize a button action payload."""
    record = _as_optional_record(value)
    if record is None:
        return None
    action_type = _normalize_optional_lowercase_string(record.get("type"))
    if action_type == "command":
        command = _normalize_optional_string(record.get("command"))
        if command:
            return {"type": "command", "command": command}
    elif action_type == "callback":
        action_value = _normalize_optional_string(record.get("value"))
        if action_value:
            return {"type": "callback", "value": action_value}
    return None


def normalize_button(value: Any) -> MessagePresentationButton | None:
    """Normalize a single button payload."""
    record = _as_optional_record(value)
    if record is None:
        return None
    label = normalize_button_label(record.get("label"))
    if not label:
        return None
    button: MessagePresentationButton = {"label": label}
    action = normalize_button_action(record.get("action"))
    if action:
        button["action"] = action
    legacy_value = _normalize_optional_string(record.get("value"))
    if legacy_value:
        button["value"] = legacy_value
    url = _normalize_optional_string(record.get("url"))
    if url:
        button["url"] = url
    style = normalize_button_style(record.get("style"))
    if style:
        button["style"] = style
    priority = record.get("priority")
    if isinstance(priority, int) and not isinstance(priority, bool):
        button["priority"] = priority
    if isinstance(record.get("disabled"), bool):
        button["disabled"] = record["disabled"]
    if isinstance(record.get("reusable"), bool):
        button["reusable"] = record["reusable"]
    return button


def normalize_buttons(value: Any) -> list[MessagePresentationButton]:
    """Normalize a list of buttons, dropping invalid entries."""
    if not isinstance(value, list):
        return []
    result: list[MessagePresentationButton] = []
    for item in value:
        button = normalize_button(item)
        if button:
            result.append(button)
    return result
