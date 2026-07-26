"""Tests for media-understanding provider output extraction."""

from __future__ import annotations

import json

from openclaw_packages.media_understanding_common import extract_gemini_response


def test_extracts_response_from_noisy_output_with_nested_json_objects() -> None:
    assert (
        extract_gemini_response(
            "\n".join(
                [
                    "debug: invoking gemini",
                    json.dumps(
                        {
                            "response": "a useful description",
                            "usage": {
                                "inputTokens": 12,
                                "outputTokens": 4,
                            },
                        },
                    ),
                ],
            ),
        )
        == "a useful description"
    )


def test_returns_none_for_incomplete_json_object() -> None:
    assert extract_gemini_response("{") is None


def test_ignores_unmatched_quotes_in_noisy_output_before_json_object() -> None:
    assert extract_gemini_response('debug: model said "hello\n{"response":"ok"}') == "ok"


def test_ignores_braces_inside_quoted_noisy_output() -> None:
    assert extract_gemini_response('debug: "hello { world" {"response":"ok"}') == "ok"


def test_ignores_shell_quoted_json_like_noisy_output() -> None:
    assert extract_gemini_response('debug: \'{"response":"fake"}\'') is None


def test_does_not_treat_apostrophes_inside_noisy_words_as_quote_delimiters() -> None:
    assert extract_gemini_response('debug: it\'s done {"response":"ok"}') == "ok"


def test_resynchronizes_after_unmatched_brace_in_noisy_output() -> None:
    assert extract_gemini_response('debug: generated {\n{"response":"ok"}') == "ok"


def test_preserves_brace_heavy_response_text() -> None:
    response = "{" * 33
    assert extract_gemini_response(json.dumps({"response": response})) == response


def test_extracts_pretty_printed_json_output() -> None:
    assert (
        extract_gemini_response(
            json.dumps(
                {
                    "response": "pretty response",
                    "usage": {"inputTokens": 12},
                },
                indent=2,
            ),
        )
        == "pretty response"
    )


def test_preserves_pretty_printed_object_elements_inside_arrays() -> None:
    assert (
        extract_gemini_response(
            json.dumps(
                {
                    "response": "array response",
                    "items": [{"id": 1}, {"id": 2}],
                },
                indent=2,
            ),
        )
        == "array response"
    )


def test_does_not_accept_inner_response_from_malformed_trailing_object() -> None:
    assert (
        extract_gemini_response('{"response":"good"} {"meta":{"response":"bad"} broken}') == "good"
    )
    assert extract_gemini_response('{"response":"good"} {"meta":{"response":"bad"}') == "good"


def test_ignores_nested_response_inside_unfinished_outer_object() -> None:
    assert extract_gemini_response('noise {"meta":{"response":"bad"}') is None


def test_does_not_promote_child_from_malformed_outer_object() -> None:
    assert extract_gemini_response('{"response":"good"} {"meta" {"response":"bad"}}') == "good"
    assert extract_gemini_response('noise {broken {"response":"bad"}}') is None
    assert (
        extract_gemini_response('{"response":"good"}\nnoise {broken\n{"response":"bad"}}') == "good"
    )
