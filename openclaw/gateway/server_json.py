"""Gateway JSON parsing helper.

Mirrors src/gateway/server-json.ts.
"""

from __future__ import annotations

from typing import Any

def safe_parse_json(*args: Any, **kwargs: Any) -> Any: ...
