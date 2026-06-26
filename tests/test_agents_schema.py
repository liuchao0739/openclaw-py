"""Tests for agents/schema helpers."""

from openclaw.agents.schema import (
    string_enum,
    optional_string_enum,
    channel_target_schema,
    channel_targets_schema,
    optional_finite_number_schema,
    optional_positive_integer_schema,
    optional_non_negative_integer_schema,
    CHANNEL_TARGET_DESCRIPTION,
)


class TestStringEnum:
    def test_basic(self):
        result = string_enum(["a", "b", "c"])
        assert result["type"] == "string"
        assert result["enum"] == ["a", "b", "c"]

    def test_empty(self):
        result = string_enum([])
        assert result["type"] == "string"
        assert "enum" not in result

    def test_with_options(self):
        result = string_enum(["x"], {"description": "test", "default": "x"})
        assert result["description"] == "test"
        assert result["default"] == "x"

    def test_optional(self):
        result = optional_string_enum(["a"])
        assert "anyOf" in result
        assert len(result["anyOf"]) == 2


class TestChannelSchemas:
    def test_target_schema(self):
        result = channel_target_schema()
        assert result["type"] == "string"
        assert "description" in result

    def test_target_custom_desc(self):
        result = channel_target_schema("custom")
        assert result["description"] == "custom"

    def test_targets_schema(self):
        result = channel_targets_schema()
        assert result["type"] == "array"
        assert "items" in result

    def test_description_constant(self):
        assert isinstance(CHANNEL_TARGET_DESCRIPTION, str)


class TestNumberSchemas:
    def test_optional_finite_number(self):
        result = optional_finite_number_schema()
        assert "anyOf" in result

    def test_optional_finite_number_with_options(self):
        result = optional_finite_number_schema({"minimum": 0, "maximum": 100})
        assert result["anyOf"][0]["minimum"] == 0

    def test_optional_positive_integer(self):
        result = optional_positive_integer_schema()
        assert result["anyOf"][0]["type"] == "integer"
        assert result["anyOf"][0]["minimum"] == 1

    def test_optional_non_negative_integer(self):
        result = optional_non_negative_integer_schema()
        assert result["anyOf"][0]["type"] == "integer"
        assert result["anyOf"][0]["minimum"] == 0

    def test_positive_integer_with_description(self):
        result = optional_positive_integer_schema({"description": "count"})
        assert result["anyOf"][0]["description"] == "count"
