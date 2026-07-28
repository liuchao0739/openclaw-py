"""Node list parsing helpers normalize node inventory records."""

from __future__ import annotations

from typing import Any


def _as_record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def parse_pairing_list(value: Any) -> dict[str, list[Any]]:
    obj = _as_record(value)
    pending = obj.get("pending")
    paired = obj.get("paired")
    return {
        "pending": pending if isinstance(pending, list) else [],
        "paired": paired if isinstance(paired, list) else [],
    }


def parse_node_list(value: Any) -> list[Any]:
    obj = _as_record(value)
    nodes = obj.get("nodes")
    return nodes if isinstance(nodes, list) else []
