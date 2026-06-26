"""Tests for plugin-sdk param readers."""

from openclaw.plugin_sdk import (
    read_string_param,
    read_number_param,
    read_finite_number_param,
    read_positive_integer_param,
    read_non_negative_integer_param,
    read_string_array_param,
    read_string_or_number_param,
)


class TestReadStringParam:
    def test_valid(self):
        assert read_string_param({"name": "hello"}, "name") == "hello"

    def test_default(self):
        assert read_string_param({}, "name", "default") == "default"

    def test_non_string(self):
        assert read_string_param({"name": 123}, "name") is None


class TestReadNumberParam:
    def test_int(self):
        assert read_number_param({"x": 5}, "x") == 5.0

    def test_float(self):
        assert read_number_param({"x": 3.14}, "x") == 3.14

    def test_bool_rejected(self):
        assert read_number_param({"x": True}, "x") is None

    def test_default(self):
        assert read_number_param({}, "x", 0.0) == 0.0


class TestReadFiniteNumberParam:
    def test_valid(self):
        assert read_finite_number_param({"x": 5}, "x") == 5.0

    def test_nan_rejected(self):
        assert read_finite_number_param({"x": float("nan")}, "x") is None

    def test_inf_rejected(self):
        assert read_finite_number_param({"x": float("inf")}, "x") is None


class TestReadPositiveIntegerParam:
    def test_valid(self):
        assert read_positive_integer_param({"x": 5}, "x") == 5

    def test_zero_rejected(self):
        assert read_positive_integer_param({"x": 0}, "x") is None

    def test_negative_rejected(self):
        assert read_positive_integer_param({"x": -1}, "x") is None

    def test_float_rejected(self):
        assert read_positive_integer_param({"x": 5.5}, "x") is None

    def test_float_whole(self):
        assert read_positive_integer_param({"x": 5.0}, "x") == 5


class TestReadNonNegativeIntegerParam:
    def test_zero(self):
        assert read_non_negative_integer_param({"x": 0}, "x") == 0

    def test_positive(self):
        assert read_non_negative_integer_param({"x": 5}, "x") == 5

    def test_negative_rejected(self):
        assert read_non_negative_integer_param({"x": -1}, "x") is None


class TestReadStringArrayParam:
    def test_valid(self):
        assert read_string_array_param({"x": ["a", "b"]}, "x") == ["a", "b"]

    def test_filters_non_strings(self):
        assert read_string_array_param({"x": ["a", 1, "b"]}, "x") == ["a", "b"]

    def test_default(self):
        assert read_string_array_param({}, "x", []) == []

    def test_non_list(self):
        assert read_string_array_param({"x": "not a list"}, "x") is None


class TestReadStringOrNumberParam:
    def test_string(self):
        assert read_string_or_number_param({"x": "hello"}, "x") == "hello"

    def test_number(self):
        assert read_string_or_number_param({"x": 42}, "x") == 42

    def test_bool_rejected(self):
        assert read_string_or_number_param({"x": True}, "x") is None

    def test_default(self):
        assert read_string_or_number_param({}, "x", "default") == "default"
