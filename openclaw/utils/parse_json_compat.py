from __future__ import annotations

import json
from typing import Any

try:
    import json5

    _HAS_JSON5 = True
except ImportError:
    _HAS_JSON5 = False


def parse_json_with_json5_fallback(raw: str) -> Any:
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        if _HAS_JSON5:
            return json5.loads(raw)
        raise
