"""Converts planned tool entries into protocol payloads for model runtimes.

Mirrors src/tools/protocol.ts.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolProtocolDescriptor:
    """Shared descriptor shape for model/provider adapters."""

    name: str
    description: str
    input_schema: dict[str, Any]


def to_tool_protocol_descriptor(entry: Mapping[str, Any]) -> ToolProtocolDescriptor:
    """Convert a tool plan entry to a protocol descriptor."""
    descriptor = entry.get("descriptor") or {}
    return ToolProtocolDescriptor(
        name=descriptor.get("name", ""),
        description=descriptor.get("description", ""),
        input_schema=descriptor.get("input_schema", {}),
    )


def to_tool_protocol_descriptors(
    entries: list[Mapping[str, Any]],
) -> list[ToolProtocolDescriptor]:
    """Convert a list of tool plan entries to protocol descriptors."""
    return [to_tool_protocol_descriptor(entry) for entry in entries]
