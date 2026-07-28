from __future__ import annotations

import math
from typing import Any, TypedDict


class GatewayCallOptions(TypedDict, total=False):
    gatewayUrl: str
    gatewayToken: str
    timeoutMs: int


def read_gateway_call_options(params: dict[str, Any]) -> GatewayCallOptions:
    opts: GatewayCallOptions = {}
    url = params.get("gatewayUrl")
    if isinstance(url, str) and url.strip():
        opts["gatewayUrl"] = url.strip()
    token = params.get("gatewayToken")
    if isinstance(token, str) and token.strip():
        opts["gatewayToken"] = token.strip()
    timeout_ms = read_positive_integer_param(params, "timeoutMs")
    if timeout_ms is not None:
        opts["timeoutMs"] = timeout_ms
    return opts


def read_trimmed_string(params: dict[str, Any], key: str) -> str:
    value = params.get(key)
    return value.strip() if isinstance(value, str) else ""


def read_boolean(params: dict[str, Any], key: str, default_value: bool = False) -> bool:
    value = params.get(key)
    if isinstance(value, bool):
        return value
    return default_value


def read_clamped_int(
    input_dict: dict[str, Any],
    key: str,
    default_value: int,
    hard_min: int,
    hard_max: int,
) -> int:
    requested = read_positive_integer_param(input_dict, key)
    if requested is None:
        requested = default_value
    return max(hard_min, min(requested, hard_max))


def human_size(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val} B"
    if bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    return f"{bytes_val / (1024 * 1024):.2f} MB"


def read_positive_integer_param(params: dict[str, Any], key: str) -> int | None:
    value = params.get(key)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        parsed = int(value)
        if parsed >= 0:
            return parsed
    if isinstance(value, str):
        try:
            parsed = int(value)
            if parsed >= 0:
                return parsed
        except ValueError:
            pass
    return None