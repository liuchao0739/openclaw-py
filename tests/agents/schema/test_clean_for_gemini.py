"""Tests for Gemini schema cleaner (P2-0016)."""

from openclaw.agents.schema.clean_for_gemini import clean_schema_for_gemini


def test_coerces_null_properties():
    cleaned = clean_schema_for_gemini({"type": "object", "properties": None})
    assert cleaned["type"] == "object"
    assert cleaned["properties"] == {}


def test_coerces_invalid_properties():
    cleaned = clean_schema_for_gemini({"type": "object", "properties": "invalid"})
    assert cleaned["properties"] == {}


def test_filters_required_not_in_properties():
    cleaned = clean_schema_for_gemini(
        {
            "type": "object",
            "properties": {"action": {"type": "string"}, "amount": {"type": "number"}},
            "required": ["action", "amount", "token"],
        }
    )
    assert cleaned["required"] == ["action", "amount"]


def test_removes_required_when_no_match():
    cleaned = clean_schema_for_gemini(
        {
            "type": "object",
            "properties": {"action": {"type": "string"}},
            "required": ["missing_a", "missing_b"],
        }
    )
    assert "required" not in cleaned


def test_strips_empty_required():
    cleaned = clean_schema_for_gemini(
        {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": [],
        }
    )
    assert "required" not in cleaned


def test_strips_not_keyword():
    cleaned = clean_schema_for_gemini(
        {
            "type": "object",
            "not": {"const": True},
            "properties": {"name": {"type": "string"}},
        }
    )
    assert "not" not in cleaned
    assert cleaned["properties"] == {"name": {"type": "string"}}


def test_collapses_type_array_strips_null():
    cleaned = clean_schema_for_gemini(
        {"type": ["string", "null"], "description": "nullable field"}
    )
    assert cleaned["type"] == "string"
    assert cleaned["description"] == "nullable field"