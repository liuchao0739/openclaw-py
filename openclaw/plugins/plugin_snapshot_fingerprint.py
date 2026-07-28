from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_plugin_snapshot_fingerprint(
    snapshot: dict[str, Any],
) -> str:
    content = json.dumps(snapshot, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def verify_plugin_snapshot(
    snapshot: dict[str, Any],
    expected_fingerprint: str,
) -> bool:
    actual = compute_plugin_snapshot_fingerprint(snapshot)
    return actual == expected_fingerprint
