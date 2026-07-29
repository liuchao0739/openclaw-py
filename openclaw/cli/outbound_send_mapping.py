from __future__ import annotations

from typing import Any


def map_outbound_send_payload(payload: dict) -> dict:
    return dict(payload)


def normalize_outbound_send_target(target: Any) -> str | None:
    if isinstance(target, str):
        return target.strip() or None
    return None
