"""Tests credential eligibility and expiry classification."""

from openclaw.agents.auth_profiles.credential_state import (
    DEFAULT_OAUTH_REFRESH_MARGIN_MS,
    evaluate_stored_credential_eligibility,
    has_usable_oauth_credential,
    resolve_token_expiry_state,
)

NOW = 1_700_000_000_000


def test_resolve_token_expiry_state_missing():
    assert resolve_token_expiry_state(None, NOW) == "missing"


def test_resolve_token_expiry_state_invalid():
    assert resolve_token_expiry_state(0, NOW) == "invalid_expires"
    assert resolve_token_expiry_state(-1, NOW) == "invalid_expires"
    assert resolve_token_expiry_state(float("nan"), NOW) == "invalid_expires"
    assert resolve_token_expiry_state(float("inf"), NOW) == "invalid_expires"
    assert resolve_token_expiry_state(8_700_000_000_000_000, NOW) == "invalid_expires"


def test_resolve_token_expiry_state_expired_and_valid():
    assert resolve_token_expiry_state(NOW - 1, NOW) == "expired"
    assert resolve_token_expiry_state(NOW + 1, NOW) == "valid"


def test_resolve_token_expiry_state_expiring():
    assert (
        resolve_token_expiry_state(
            NOW + DEFAULT_OAUTH_REFRESH_MARGIN_MS - 1,
            NOW,
            expiring_within_ms=DEFAULT_OAUTH_REFRESH_MARGIN_MS,
        )
        == "expiring"
    )


def test_has_usable_oauth_near_expiry():
    assert (
        has_usable_oauth_credential(
            {
                "type": "oauth",
                "provider": "openai",
                "access": "access-token",
                "refresh": "refresh-token",
                "expires": NOW + DEFAULT_OAUTH_REFRESH_MARGIN_MS - 1,
            },
            now=NOW,
        )
        is False
    )


def test_evaluate_api_key_ref():
    result = evaluate_stored_credential_eligibility(
        credential={
            "type": "api_key",
            "provider": "anthropic",
            "keyRef": {"source": "env", "provider": "default", "id": "ANTHROPIC_API_KEY"},
        },
        now=NOW,
    )
    assert result == {"eligible": True, "reasonCode": "ok"}


def test_evaluate_token_ref():
    result = evaluate_stored_credential_eligibility(
        credential={
            "type": "token",
            "provider": "github-copilot",
            "tokenRef": {"source": "env", "provider": "default", "id": "GITHUB_TOKEN"},
        },
        now=NOW,
    )
    assert result == {"eligible": True, "reasonCode": "ok"}


def test_evaluate_token_invalid_expires():
    result = evaluate_stored_credential_eligibility(
        credential={"type": "token", "provider": "x", "token": "tok", "expires": 0},
        now=NOW,
    )
    assert result == {"eligible": False, "reasonCode": "invalid_expires"}


def test_evaluate_oauth_missing_material():
    result = evaluate_stored_credential_eligibility(
        credential={
            "type": "oauth",
            "provider": "openai",
            "access": "",
            "refresh": "",
            "expires": NOW + 60_000,
        },
        now=NOW,
    )
    assert result == {"eligible": False, "reasonCode": "missing_credential"}