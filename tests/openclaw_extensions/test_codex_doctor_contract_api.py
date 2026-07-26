"""Tests for Codex doctor contract API."""

from __future__ import annotations

from openclaw_extensions.codex.doctor_contract_api import (
    legacy_config_rules,
    normalize_compatibility_config,
)


def test_reports_the_retired_dynamic_tools_profile_config_key() -> None:
    assert legacy_config_rules[0]["match"](
        {
            "codexDynamicToolsProfile": "openclaw-compat",
            "codexDynamicToolsLoading": "direct",
        }
    )
    assert not legacy_config_rules[0]["match"]({"codexDynamicToolsLoading": "direct"})


def test_reports_old_approval_routed_destructive_plugin_policy_values() -> None:
    assert legacy_config_rules[1]["match"](
        {
            "allow_destructive_actions": "on-request",
            "plugins": {},
        }
    )
    assert legacy_config_rules[1]["match"](
        {
            "allow_destructive_actions": True,
            "plugins": {
                "google-calendar": {"allow_destructive_actions": "on-request"},
            },
        }
    )
    assert not legacy_config_rules[1]["match"](
        {
            "allow_destructive_actions": "auto",
            "plugins": {
                "google-calendar": {"allow_destructive_actions": True},
            },
        }
    )


def test_removes_the_retired_dynamic_tools_profile_without_dropping_other_codex_config() -> None:
    original = {
        "plugins": {
            "entries": {
                "codex": {
                    "enabled": True,
                    "config": {
                        "codexDynamicToolsProfile": "openclaw-compat",
                        "codexDynamicToolsLoading": "direct",
                        "codexDynamicToolsExclude": ["custom_tool"],
                        "appServer": {"mode": "guardian"},
                    },
                }
            }
        }
    }

    result = normalize_compatibility_config({"cfg": original})

    assert result["changes"] == [
        (
            "Removed retired plugins.entries.codex.config.codexDynamicToolsProfile; "
            "Codex app-server always keeps Codex-native workspace tools native."
        ),
    ]
    assert result["config"]["plugins"]["entries"]["codex"]["config"] == {
        "codexDynamicToolsLoading": "direct",
        "codexDynamicToolsExclude": ["custom_tool"],
        "appServer": {"mode": "guardian"},
    }
    assert "codexDynamicToolsProfile" in original["plugins"]["entries"]["codex"]["config"]


def test_renames_old_approval_routed_destructive_plugin_policy_values() -> None:
    original = {
        "plugins": {
            "entries": {
                "codex": {
                    "enabled": True,
                    "config": {
                        "codexDynamicToolsProfile": "openclaw-compat",
                        "codexPlugins": {
                            "enabled": True,
                            "allow_destructive_actions": "on-request",
                            "plugins": {
                                "google-calendar": {
                                    "enabled": True,
                                    "allow_destructive_actions": "on-request",
                                },
                                "slack": {
                                    "enabled": True,
                                    "allow_destructive_actions": False,
                                },
                            },
                        },
                    },
                }
            }
        }
    }

    result = normalize_compatibility_config({"cfg": original})

    assert result["changes"] == [
        (
            "Removed retired plugins.entries.codex.config.codexDynamicToolsProfile; "
            "Codex app-server always keeps Codex-native workspace tools native."
        ),
        (
            'Renamed plugins.entries.codex.config.codexPlugins allow_destructive_actions="on-request" '
            'values to "auto".'
        ),
    ]
    assert result["config"]["plugins"]["entries"]["codex"]["config"] == {
        "codexPlugins": {
            "enabled": True,
            "allow_destructive_actions": "auto",
            "plugins": {
                "google-calendar": {
                    "enabled": True,
                    "allow_destructive_actions": "auto",
                },
                "slack": {
                    "enabled": True,
                    "allow_destructive_actions": False,
                },
            },
        }
    }
    assert (
        original["plugins"]["entries"]["codex"]["config"]["codexPlugins"]["plugins"][
            "google-calendar"
        ]["allow_destructive_actions"]
        == "on-request"
    )
