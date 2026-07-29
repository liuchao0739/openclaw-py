from __future__ import annotations

from typing import Any


def collect_startup_metadata() -> dict:
    import os
    import sys

    return {
        "pid": os.getpid(),
        "platform": sys.platform,
        "python": sys.version,
    }


def format_startup_metadata(metadata: dict) -> str:
    import json

    return json.dumps(metadata, indent=2)
