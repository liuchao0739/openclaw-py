from typing import Any, Dict, List, Literal

CANVAS_ACTIONS: List[str] = [
    "present",
    "hide",
    "navigate",
    "eval",
    "snapshot",
    "a2ui_push",
    "a2ui_reset",
]

CANVAS_SNAPSHOT_FORMATS: List[str] = ["png", "jpg", "jpeg"]


def _string_enum(values: List[str]) -> Dict[str, Any]:
    return {"type": "string", "enum": list(values)}


def _optional_string() -> Dict[str, Any]:
    return {"type": "string"}


def _optional_positive_integer() -> Dict[str, Any]:
    return {"type": "integer", "minimum": 1}


def _optional_non_negative_integer() -> Dict[str, Any]:
    return {"type": "integer", "minimum": 0}


def _optional_finite_number(extra: Dict[str, Any] = None) -> Dict[str, Any]:
    result = {"type": "number"}
    if extra:
        result.update(extra)
    return result


CanvasToolSchema: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": _string_enum(CANVAS_ACTIONS),
        "gatewayUrl": _optional_string(),
        "gatewayToken": _optional_string(),
        "timeoutMs": _optional_positive_integer(),
        "node": _optional_string(),
        "target": _optional_string(),
        "x": _optional_finite_number(),
        "y": _optional_finite_number(),
        "width": _optional_finite_number(),
        "height": _optional_finite_number(),
        "url": _optional_string(),
        "javaScript": _optional_string(),
        "outputFormat": _string_enum(CANVAS_SNAPSHOT_FORMATS),
        "maxWidth": _optional_positive_integer(),
        "quality": _optional_finite_number({"minimum": 0, "maximum": 1}),
        "delayMs": _optional_non_negative_integer(),
        "jsonl": _optional_string(),
        "jsonlPath": _optional_string(),
    },
    "required": ["action"],
}
