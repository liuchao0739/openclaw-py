from __future__ import annotations

import base64
import hashlib
import re
from typing import Any


def _looks_like_connection_bound_id(id_str: str) -> bool:
    if len(id_str) < 24:
        return False
    if re.match(r"^(?:rs|msg|fc)_[A-Za-z0-9_-]+$", id_str):
        return False
    if not re.match(r"^[A-Za-z0-9+/_-]+=*$", id_str):
        return False
    try:
        decoded = base64.b64decode(id_str)
        return len(decoded) >= 16
    except Exception:
        return False


def _derive_replacement_id(type_str: str | None, original_id: str) -> str:
    prefix = "fc" if type_str == "function_call" else "msg"
    hex_digest = hashlib.sha256(original_id.encode()).hexdigest()[:16]
    return f"{prefix}_{hex_digest}"


def _is_input_item(value: Any) -> bool:
    return isinstance(value, dict)


def _is_valid_reasoning_replay_id(id_val: Any) -> bool:
    return isinstance(id_val, str) and 0 < len(id_val) <= 64


def sanitize_copilot_replay_response_ids(input_data: Any) -> bool:
    if not isinstance(input_data, list):
        return False
    rewrote = False
    for index in range(len(input_data) - 1, -1, -1):
        item = input_data[index]
        if not _is_input_item(item):
            continue
        item_id = item.get("id")
        if item.get("type") == "reasoning":
            if item_id is not None and not _is_valid_reasoning_replay_id(item_id):
                del input_data[index]
                rewrote = True
            continue
        if not isinstance(item_id, str) or len(item_id) == 0:
            continue
        if _looks_like_connection_bound_id(item_id):
            item["id"] = _derive_replacement_id(
                item.get("type") if isinstance(item.get("type"), str) else None,
                item_id,
            )
            rewrote = True
    return rewrote


def rewrite_copilot_connection_bound_response_ids(input_data: Any) -> bool:
    return sanitize_copilot_replay_response_ids(input_data)


def sanitize_copilot_replay_response_payload_ids(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    return sanitize_copilot_replay_response_ids(payload.get("input"))


def rewrite_copilot_response_payload_connection_bound_ids(payload: Any) -> bool:
    return sanitize_copilot_replay_response_payload_ids(payload)
