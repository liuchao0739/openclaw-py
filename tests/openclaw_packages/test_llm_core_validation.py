"""Tests for llm-core validation behavior.

Mirrors packages/llm-core/src/validation.test.ts.
"""

from __future__ import annotations

import pytest

from openclaw_packages.llm_core import validate_tool_arguments

DECIMAL_TOOL = {
    "name": "decimal-tool",
    "description": "test tool",
    "parameters": {
        "type": "object",
        "properties": {
            "amount": {"type": "number"},
            "count": {"type": "integer"},
        },
        "required": ["amount", "count"],
        "additionalProperties": False,
    },
}


def test_coerces_strict_decimal_numeric_strings_for_plain_json_schemas() -> None:
    assert validate_tool_arguments(
        DECIMAL_TOOL,
        {
            "type": "toolCall",
            "id": "call-1",
            "name": "decimal-tool",
            "arguments": {"amount": "1e3", "count": "+3"},
        },
    ) == {"amount": 1000, "count": 3}


def test_rejects_non_decimal_numeric_strings_for_plain_json_schemas() -> None:
    with pytest.raises(ValueError, match='Validation failed for tool "decimal-tool"'):
        validate_tool_arguments(
            DECIMAL_TOOL,
            {
                "type": "toolCall",
                "id": "call-1",
                "name": "decimal-tool",
                "arguments": {"amount": "0x10", "count": "0b10"},
            },
        )
