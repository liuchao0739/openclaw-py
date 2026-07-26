"""Defines built-in tool descriptors exposed to model planning.

Mirrors src/tools/descriptors.ts.
"""

from __future__ import annotations

from collections.abc import Sequence

from openclaw.tools.types import ToolDescriptor


def define_tool_descriptor(descriptor: ToolDescriptor) -> ToolDescriptor:
    """Define one tool descriptor without changing its runtime shape."""
    return descriptor


def define_tool_descriptors(
    descriptors: Sequence[ToolDescriptor],
) -> Sequence[ToolDescriptor]:
    """Define a readonly descriptor list without changing runtime order or entries."""
    return descriptors
