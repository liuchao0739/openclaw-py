"""Tests for cron/store core modules."""

import json
import os

import pytest

from openclaw.cron.store.key import cron_store_key
from openclaw.cron.store.scalar_codec import (
    parse_json_object,
    parse_json_value,
    normalize_number,
    boolean_to_integer,
    integer_to_boolean,
    serialize_json,
    parse_json_array,
)


class TestCronStoreKey:
    def test_resolves_path(self, tmp_path):
        key = cron_store_key(str(tmp_path / "store.db"))
        assert key.endswith("store.db")

    def test_absolute(self, tmp_path):
        key = cron_store_key(str(tmp_path))
        assert os.path.isabs(key)

    def test_idempotent(self, tmp_path):
        k1 = cron_store_key(str(tmp_path / "x"))
        k2 = cron_store_key(str(tmp_path / "x"))
        assert k1 == k2


class TestScalarCodec:
    def test_parse_json_object_valid(self):
        assert parse_json_object('{"a": 1}', {}) == {"a": 1}

    def test_parse_json_object_non_object(self):
        assert parse_json_object('[1, 2]', {}) == {}

    def test_parse_json_object_malformed(self):
        assert parse_json_object("not json", {"default": True}) == {"default": True}

    def test_parse_json_value_valid(self):
        assert parse_json_value('[1, 2]', None) == [1, 2]

    def test_parse_json_value_string(self):
        assert parse_json_value('"hello"', None) == "hello"

    def test_parse_json_value_malformed(self):
        assert parse_json_value("not json", "fallback") == "fallback"

    def test_normalize_number_int(self):
        assert normalize_number(42) == 42

    def test_normalize_number_float(self):
        assert normalize_number(3.14) == 3.14

    def test_normalize_number_none(self):
        assert normalize_number(None) is None

    def test_normalize_number_bool(self):
        assert normalize_number(True) is None

    def test_normalize_number_string_int(self):
        assert normalize_number("123") == 123

    def test_normalize_number_string_float(self):
        assert normalize_number("1.5") == 1.5

    def test_normalize_number_invalid_string(self):
        assert normalize_number("abc") is None

    def test_boolean_to_integer_true(self):
        assert boolean_to_integer(True) == 1

    def test_boolean_to_integer_false(self):
        assert boolean_to_integer(False) == 0

    def test_boolean_to_integer_none(self):
        assert boolean_to_integer(None) is None

    def test_integer_to_boolean_one(self):
        assert integer_to_boolean(1) is True

    def test_integer_to_boolean_zero(self):
        assert integer_to_boolean(0) is False

    def test_integer_to_boolean_none(self):
        assert integer_to_boolean(None) is None

    def test_integer_to_boolean_string(self):
        assert integer_to_boolean("1") is True

    def test_serialize_json_value(self):
        assert serialize_json({"a": 1}) == '{"a": 1}'

    def test_serialize_json_none(self):
        assert serialize_json(None) is None

    def test_serialize_json_list(self):
        result = serialize_json([1, 2])
        assert json.loads(result) == [1, 2]

    def test_parse_json_array_valid(self):
        assert parse_json_array('["a", "b"]') == ["a", "b"]

    def test_parse_json_array_filters_non_strings(self):
        assert parse_json_array('["a", 1, "b", null]') == ["a", "b"]

    def test_parse_json_array_none(self):
        assert parse_json_array(None) is None

    def test_parse_json_array_empty(self):
        assert parse_json_array("") is None

    def test_parse_json_array_non_array(self):
        assert parse_json_array('{"a": 1}') is None
