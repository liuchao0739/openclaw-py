"""Tests for normalization-core string normalization."""

from __future__ import annotations

import pytest

from openclaw_packages.normalization_core.string_normalization import (
    normalize_at_hash_slug,
    normalize_hyphen_slug,
    normalize_sorted_unique_string_entries,
    normalize_sorted_unique_trimmed_string_list,
    normalize_string_entries,
    normalize_string_entries_lower,
    normalize_unique_single_or_trimmed_string_list,
    normalize_unique_string_entries,
    normalize_unique_string_entries_lower,
    normalize_unique_trimmed_string_list,
    sort_unique_strings,
    unique_strings,
)


def test_normalizes_mixed_allow_list_entries() -> None:
    assert normalize_string_entries([" a ", 42, "", "  ", "z"]) == ["a", "42", "z"]
    assert normalize_string_entries(
        [" ok ", None, type("Obj", (), {"__str__": lambda self: " obj "})()]
    ) == [
        "ok",
        "None",
        "obj",
    ]
    assert normalize_string_entries(None) == []


def test_normalizes_mixed_allow_list_entries_to_lowercase() -> None:
    assert normalize_string_entries_lower([" A ", "MiXeD", 7]) == ["a", "mixed", "7"]


def test_sorts_unique_string_values() -> None:
    assert sort_unique_strings(["b", "a", "b"]) == ["a", "b"]


def test_deduplicates_string_values_while_preserving_first_seen_order() -> None:
    assert unique_strings(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]


def test_normalizes_unique_string_entries() -> None:
    assert normalize_unique_string_entries([" b ", "a", "b", "", 4, "a"]) == ["b", "a", "4"]


def test_normalizes_unique_lowercase_string_entries() -> None:
    assert normalize_unique_string_entries_lower([" A ", "a", "MiXeD", "", 7]) == [
        "a",
        "mixed",
        "7",
    ]


def test_normalizes_sorted_unique_string_entries() -> None:
    assert normalize_sorted_unique_string_entries([" b ", "a", "b", "", 4]) == ["4", "a", "b"]


def test_normalizes_unique_trimmed_string_lists() -> None:
    assert normalize_unique_trimmed_string_list([" b ", "a", "b", "", "a"]) == ["b", "a"]
    assert normalize_unique_trimmed_string_list("b") == []


def test_normalizes_sorted_unique_trimmed_string_lists() -> None:
    assert normalize_sorted_unique_trimmed_string_list([" b ", "a", "b", "", "a"]) == ["a", "b"]
    assert normalize_sorted_unique_trimmed_string_list(["z", 1, " a "]) == ["a", "z"]


def test_normalizes_unique_single_or_list_string_values() -> None:
    assert normalize_unique_single_or_trimmed_string_list([" b ", "a", "b", "", "a"]) == [
        "b",
        "a",
    ]
    assert normalize_unique_single_or_trimmed_string_list(" b ") == ["b"]


def test_normalizes_slug_like_labels_while_preserving_supported_symbols() -> None:
    assert normalize_hyphen_slug("  Team Room  ") == "team-room"
    assert normalize_hyphen_slug(" #My_Channel + Alerts ") == "#my_channel-+-alerts"
    assert normalize_hyphen_slug("..foo---bar..") == "foo-bar"
    assert normalize_hyphen_slug(None) == ""
    assert normalize_hyphen_slug("") == ""


def test_collapses_repeated_separators_and_trims_leading_trailing_punctuation() -> None:
    assert normalize_hyphen_slug("  ...Hello   /  World---  ") == "hello-world"
    assert normalize_hyphen_slug(" ###Team@@@Room### ") == "###team@@@room###"


def test_normalizes_at_hash_prefixed_slugs_used_by_channel_allowlists() -> None:
    assert normalize_at_hash_slug(" #My_Channel + Alerts ") == "my-channel-alerts"
    assert normalize_at_hash_slug("@@Room___Name") == "room-name"
    assert normalize_at_hash_slug(None) == ""
    assert normalize_at_hash_slug("") == ""


def test_strips_repeated_prefixes_and_collapses_separator_only_results() -> None:
    assert normalize_at_hash_slug("###__Room  Name__") == "room-name"
    assert normalize_at_hash_slug("@@@___") == ""


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        ("技术讨论组", "技术讨论组"),
        ("  AI 助手群  ", "ai-助手群"),
        ("友達グループ", "友達グループ"),
        ("개발자 모임", "개발자-모임"),
        ("Team 技术讨论", "team-技术讨论"),
        ("#OpenClaw中文群", "#openclaw中文群"),
        ("Команда разработки", "команда-разработки"),
        ("فريق التطوير", "فريق-التطوير"),
    ],
)
def test_preserves_unicode_letters_in_normalize_hyphen_slug(
    input_value: str, expected: str
) -> None:
    assert normalize_hyphen_slug(input_value) == expected


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        ("Cafe\u0301 Team", "café-team"),
        ("हिन्दी चर्चा", "हिन्दी-चर्चा"),
        ("ห้อง แช็ต", "ห้อง-แช็ต"),
    ],
)
def test_preserves_combining_marks_in_normalize_hyphen_slug(
    input_value: str, expected: str
) -> None:
    assert normalize_hyphen_slug(input_value) == expected


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        ("#技术频道", "技术频道"),
        ("@中文群组", "中文群组"),
        ("#日本語チャンネル", "日本語チャンネル"),
        ("#한국어채널", "한국어채널"),
        ("#Команда разработки", "команда-разработки"),
        ("@فريق التطوير", "فريق-التطوير"),
        ("#OpenClaw中文群", "openclaw中文群"),
    ],
)
def test_preserves_unicode_letters_in_normalize_at_hash_slug(
    input_value: str, expected: str
) -> None:
    assert normalize_at_hash_slug(input_value) == expected


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        ("#Cafe\u0301_Team", "café-team"),
        ("@हिन्दी चर्चा", "हिन्दी-चर्चा"),
        ("#ห้อง แช็ต", "ห้อง-แช็ต"),
    ],
)
def test_preserves_combining_marks_in_normalize_at_hash_slug(
    input_value: str, expected: str
) -> None:
    assert normalize_at_hash_slug(input_value) == expected
