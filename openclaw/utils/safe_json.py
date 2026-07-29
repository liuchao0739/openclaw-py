from __future__ import annotations

import base64
import json
from typing import Any


def _default_serializer(obj: Any) -> Any:
    if isinstance(obj, int) and not isinstance(obj, bool):
        if obj > 2**63 - 1 or obj < -(2**63):
            return str(obj)
    if isinstance(obj, bytes):
        return {"type": "Uint8Array", "data": base64.b64encode(obj).decode("ascii")}
    if isinstance(obj, BaseException):
        return {
            "name": type(obj).__name__,
            "message": str(obj),
            "stack": getattr(obj, "__traceback__", None),
        }
    if callable(obj):
        return "[Function]"
    return None


def safe_json_stringify(value: Any) -> str | None:
    try:
        return json.dumps(value, default=_default_serializer)
    except (ValueError, TypeError):
        return None
