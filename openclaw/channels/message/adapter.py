"""Channel message adapter definition helper.

Supplies manual receive acknowledgement defaults while preserving adapter-specific types.
"""

from __future__ import annotations

from typing import Any

_DEFAULT_MANUAL_RECEIVE_ADAPTER = {
    "defaultAckPolicy": "manual",
    "supportedAckPolicies": ["manual"],
}


def define_channel_message_adapter(adapter: dict[str, Any]) -> dict[str, Any]:
    """Define a message adapter while defaulting receive acknowledgement to manual."""
    result = dict(adapter)
    if "receive" not in result or result["receive"] is None:
        result["receive"] = dict(_DEFAULT_MANUAL_RECEIVE_ADAPTER)
    return result
