"""JSON schema for the Browser agent tool."""

from __future__ import annotations

from openclaw.agents.schema import (
    optional_finite_number_schema,
    optional_non_negative_integer_schema,
    optional_positive_integer_schema,
    optional_string_enum,
    string_enum,
)

ACT_MAX_VIEWPORT_DIMENSION = 8192

BROWSER_ACT_KINDS = [
    "click",
    "clickCoords",
    "type",
    "press",
    "hover",
    "drag",
    "select",
    "fill",
    "resize",
    "wait",
    "evaluate",
    "close",
]

BROWSER_TOOL_ACTIONS = [
    "doctor",
    "status",
    "start",
    "stop",
    "profiles",
    "tabs",
    "open",
    "focus",
    "close",
    "snapshot",
    "screenshot",
    "navigate",
    "console",
    "pdf",
    "upload",
    "dialog",
    "act",
]

BROWSER_TARGETS = ["sandbox", "host", "node"]
BROWSER_SNAPSHOT_FORMATS = ["aria", "ai"]
BROWSER_SNAPSHOT_MODES = ["efficient"]
BROWSER_SNAPSHOT_REFS = ["role", "aria"]
BROWSER_IMAGE_TYPES = ["png", "jpeg"]

TAB_REFERENCE_DESCRIPTION = (
    "Tab reference. Prefer suggestedTargetId, tabId, or label from tabs output; "
    "raw CDP targetId and unique raw prefixes remain supported for compatibility."
)

BrowserActSchema = {
    "type": "object",
    "properties": {
        "kind": string_enum(BROWSER_ACT_KINDS),
        "targetId": {"type": "string", "description": TAB_REFERENCE_DESCRIPTION},
        "ref": {"type": "string"},
        "doubleClick": {"type": "boolean"},
        "button": {"type": "string"},
        "modifiers": {"type": "array", "items": {"type": "string"}},
        "x": optional_finite_number_schema(),
        "y": optional_finite_number_schema(),
        "text": {"type": "string"},
        "submit": {"type": "boolean"},
        "slowly": {"type": "boolean"},
        "key": {"type": "string"},
        "delayMs": optional_non_negative_integer_schema(),
        "startRef": {"type": "string"},
        "endRef": {"type": "string"},
        "values": {"type": "array", "items": {"type": "string"}},
        "fields": {
            "type": "array",
            "items": {"type": "object", "additionalProperties": True},
        },
        "width": optional_positive_integer_schema({"maximum": ACT_MAX_VIEWPORT_DIMENSION}),
        "height": optional_positive_integer_schema({"maximum": ACT_MAX_VIEWPORT_DIMENSION}),
        "timeMs": optional_non_negative_integer_schema(),
        "selector": {"type": "string"},
        "url": {"type": "string"},
        "loadState": {"type": "string"},
        "textGone": {"type": "string"},
        "timeoutMs": optional_positive_integer_schema(),
        "fn": {"type": "string"},
    },
    "required": ["kind"],
    "additionalProperties": False,
}

BrowserToolSchema = {
    "type": "object",
    "properties": {
        "action": string_enum(BROWSER_TOOL_ACTIONS),
        "target": optional_string_enum(BROWSER_TARGETS),
        "node": {"type": "string"},
        "profile": {"type": "string"},
        "targetUrl": {"type": "string"},
        "url": {"type": "string"},
        "targetId": {"type": "string", "description": TAB_REFERENCE_DESCRIPTION},
        "label": {"type": "string"},
        "limit": optional_positive_integer_schema(),
        "maxChars": optional_non_negative_integer_schema(),
        "mode": optional_string_enum(BROWSER_SNAPSHOT_MODES),
        "snapshotFormat": optional_string_enum(BROWSER_SNAPSHOT_FORMATS),
        "refs": optional_string_enum(BROWSER_SNAPSHOT_REFS),
        "interactive": {"type": "boolean"},
        "compact": {"type": "boolean"},
        "depth": optional_non_negative_integer_schema(),
        "selector": {"type": "string"},
        "frame": {"type": "string"},
        "labels": {"type": "boolean"},
        "urls": {"type": "boolean"},
        "fullPage": {"type": "boolean"},
        "ref": {"type": "string"},
        "element": {"type": "string"},
        "type": optional_string_enum(BROWSER_IMAGE_TYPES),
        "level": {"type": "string"},
        "paths": {"type": "array", "items": {"type": "string"}},
        "inputRef": {"type": "string"},
        "timeoutMs": optional_positive_integer_schema(),
        "dialogId": {"type": "string"},
        "accept": {"type": "boolean"},
        "promptText": {"type": "string"},
        "kind": optional_string_enum(BROWSER_ACT_KINDS),
        "doubleClick": {"type": "boolean"},
        "button": {"type": "string"},
        "modifiers": {"type": "array", "items": {"type": "string"}},
        "x": optional_finite_number_schema(),
        "y": optional_finite_number_schema(),
        "text": {"type": "string"},
        "submit": {"type": "boolean"},
        "slowly": {"type": "boolean"},
        "key": {"type": "string"},
        "delayMs": optional_non_negative_integer_schema(),
        "startRef": {"type": "string"},
        "endRef": {"type": "string"},
        "values": {"type": "array", "items": {"type": "string"}},
        "fields": {
            "type": "array",
            "items": {"type": "object", "additionalProperties": True},
        },
        "width": optional_positive_integer_schema({"maximum": ACT_MAX_VIEWPORT_DIMENSION}),
        "height": optional_positive_integer_schema({"maximum": ACT_MAX_VIEWPORT_DIMENSION}),
        "timeMs": optional_non_negative_integer_schema(),
        "textGone": {"type": "string"},
        "loadState": {"type": "string"},
        "fn": {"type": "string"},
        "request": BrowserActSchema,
    },
    "required": ["action"],
    "additionalProperties": False,
}
