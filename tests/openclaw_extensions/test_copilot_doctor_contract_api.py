"""Tests for copilot doctor contract API."""

from __future__ import annotations

from openclaw_extensions.copilot.doctor_contract_api import (
    legacy_config_rules,
    normalize_compatibility_config,
    session_route_state_owners,
)


def test_has_no_legacy_config_rules_at_mvp() -> None:
    assert legacy_config_rules == []


def test_normalize_compatibility_config_is_a_structural_no_op_when_no_migrations_apply() -> None:
    cfg = {
        "plugins": {
            "entries": {"copilot": {"enabled": True, "config": {"pool": {"idleTtlMs": 12345}}}}
        }
    }
    result = normalize_compatibility_config({"cfg": cfg})
    assert result["config"] is cfg
    assert result["changes"] == []


def test_declares_exactly_one_session_route_state_owner_for_copilot() -> None:
    assert len(session_route_state_owners) == 1
    owner = session_route_state_owners[0]
    assert owner["id"] == "copilot"
    assert owner["label"] == "GitHub Copilot agent runtime"


def test_claims_the_subscription_copilot_providers() -> None:
    owner = session_route_state_owners[0]
    assert owner["providerIds"] == ["github-copilot"]


def test_claims_the_copilot_runtime_session_key_and_auth_profile_prefix() -> None:
    owner = session_route_state_owners[0]
    assert owner["runtimeIds"] == ["copilot"]
    assert owner["cliSessionKeys"] == ["copilot"]
    assert owner["authProfilePrefixes"] == ["github-copilot:"]
