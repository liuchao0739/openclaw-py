from __future__ import annotations

import json
import sys
from typing import Any


def log_plugin_event(event: str, data: dict | None = None) -> None:
    payload = {"event": event, "data": data or {}}
    print(json.dumps(payload), file=sys.stderr)


def log_plugin_error(error: str, data: dict | None = None) -> None:
    payload = {"error": error, "data": data or {}}
    print(json.dumps(payload), file=sys.stderr)
