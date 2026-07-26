"""Tests for net-policy sensitive URL redaction."""

from __future__ import annotations

from openclaw_packages.net_policy import (
    SENSITIVE_URL_HINT_TAG,
    has_sensitive_url_hint_tag,
    is_sensitive_url_config_path,
    is_sensitive_url_query_param_name,
    redact_sensitive_url,
    redact_sensitive_url_like_string,
)


def test_redacts_userinfo_and_sensitive_query_params_from_valid_urls() -> None:
    assert redact_sensitive_url("https://user:pass@example.com/mcp?token=secret&safe=value") == (
        "https://***:***@example.com/mcp?token=***&safe=value"
    )


def test_treats_query_param_names_case_insensitively() -> None:
    assert redact_sensitive_url("https://example.com/mcp?Access_Token=secret") == (
        "https://example.com/mcp?Access_Token=***"
    )


def test_redacts_encoded_and_invisible_spliced_sensitive_query_param_names() -> None:
    assert (
        redact_sensitive_url("https://example.com/mcp?client%5Fse%E2%80%8Bcret=secret&safe=value")
        == "https://example.com/mcp?client_se%E2%80%8Bcret=***&safe=value"
    )


def test_redacts_encoded_sensitive_query_names_with_decoded_whitespace_and_control_separators() -> (
    None
):
    assert (
        redact_sensitive_url(
            "https://example.com/mcp?client%5Fse%20cret=space&client%5Fse%00cret=nul"
        )
        == "https://example.com/mcp?client_se+cret=***&client_se%00cret=***"
    )


def test_redacts_query_names_with_plus_encoded_separators() -> None:
    assert redact_sensitive_url("https://example.com/mcp?client_se+cret=secret&safe=value") == (
        "https://example.com/mcp?client_se+cret=***&safe=value"
    )


def test_keeps_non_sensitive_urls_unchanged() -> None:
    assert redact_sensitive_url("https://example.com/mcp?safe=value") == (
        "https://example.com/mcp?safe=value"
    )


def test_redacts_invalid_url_like_strings() -> None:
    assert redact_sensitive_url_like_string("//user:pass@example.com/mcp?client_secret=secret") == (
        "//***:***@example.com/mcp?client_secret=***"
    )


def test_redacts_encoded_and_invisible_spliced_query_names_in_invalid_url_like_strings() -> None:
    assert (
        redact_sensitive_url_like_string(
            "//example.com/mcp?client%5Fse%E2%80%8Bcret=secret&safe=value"
        )
        == "//example.com/mcp?client%5Fse%E2%80%8Bcret=***&safe=value"
    )


def test_redacts_encoded_query_names_with_decoded_whitespace_and_control_separators_in_invalid_url_like_strings() -> (
    None
):
    assert (
        redact_sensitive_url_like_string(
            "//example.com/mcp?client%5Fse%20cret=space&client%5Fse%00cret=nul"
        )
        == "//example.com/mcp?client%5Fse%20cret=***&client%5Fse%00cret=***"
    )


def test_redacts_plus_spliced_query_names_in_invalid_url_like_strings() -> None:
    assert redact_sensitive_url_like_string(
        "//example.com/mcp?client_se+cret=secret&safe=value"
    ) == ("//example.com/mcp?client_se+cret=***&safe=value")


def test_redacts_every_url_like_userinfo_occurrence_in_arbitrary_text() -> None:
    assert (
        redact_sensitive_url_like_string(
            "fatal https://a:b@github.com/one.git and https://c:d@github.com/two.git"
        )
        == "fatal https://***:***@github.com/one.git and https://***:***@github.com/two.git"
    )


def test_redacts_protocol_urls_that_are_too_malformed_to_parse() -> None:
    assert (
        redact_sensitive_url_like_string(
            "wss://fallback-user:fallback-pass@[bad-host/socket?token=fallback-secret&keep=visible)"
        )
        == "wss://***:***@[bad-host/socket?token=***&keep=visible)"
    )


def test_matches_auth_oriented_query_params_used_by_mcp_sse_config_redaction() -> None:
    assert is_sensitive_url_query_param_name("token") is True
    assert is_sensitive_url_query_param_name("refresh_token") is True
    assert is_sensitive_url_query_param_name("access-token") is True
    assert is_sensitive_url_query_param_name("hook-token") is True
    assert is_sensitive_url_query_param_name("passwd") is True
    assert is_sensitive_url_query_param_name("signature") is True
    assert is_sensitive_url_query_param_name("code") is True
    assert is_sensitive_url_query_param_name("x-amz-signature") is True
    assert is_sensitive_url_query_param_name("X-Amz-Security-Token") is True
    assert is_sensitive_url_query_param_name("id_token") is True
    assert is_sensitive_url_query_param_name("app_secret") is True
    assert is_sensitive_url_query_param_name("client%5Fse\u200bcret") is True
    assert is_sensitive_url_query_param_name("client%5Fse%20cret") is True
    assert is_sensitive_url_query_param_name("client%5Fse%00cret") is True
    assert is_sensitive_url_query_param_name("client_se+cret") is True
    assert is_sensitive_url_query_param_name("client_se\u3164cret") is True
    assert is_sensitive_url_query_param_name("credential") is True
    assert is_sensitive_url_query_param_name("safe") is False


def test_recognizes_config_paths_that_may_embed_url_secrets() -> None:
    assert is_sensitive_url_config_path("models.providers.*.baseUrl") is True
    assert is_sensitive_url_config_path("mcp.servers.remote.url") is True
    assert is_sensitive_url_config_path("gateway.remote.url") is False


def test_recognizes_cdp_url_config_paths_as_sensitive() -> None:
    assert is_sensitive_url_config_path("browser.cdpUrl") is True
    assert is_sensitive_url_config_path("browser.profiles.remote.cdpUrl") is True
    assert is_sensitive_url_config_path("browser.profiles.staging.cdpUrl") is True


def test_uses_explicit_url_secret_hint_tag() -> None:
    assert SENSITIVE_URL_HINT_TAG == "url-secret"
    assert has_sensitive_url_hint_tag({"tags": [SENSITIVE_URL_HINT_TAG]}) is True
    assert has_sensitive_url_hint_tag({"tags": ["security"]}) is False
