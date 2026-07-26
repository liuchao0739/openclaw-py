"""Tests for openclaw.tools.availability — mirrors src/tools/availability.test.ts."""

from __future__ import annotations

from openclaw.packages.normalization_core import is_record
from openclaw.tools.availability import evaluate_tool_availability
from openclaw.tools.types import ToolDescriptor

_BASE_DESCRIPTOR: ToolDescriptor = {
    "name": "example",
    "description": "Example tool",
    "input_schema": {"type": "object"},
    "owner": {"kind": "core"},
    "executor": {"kind": "core", "executor_id": "example"},
}


class TestEvaluateToolAvailability:
    def test_treats_descriptors_without_signals_as_available(self) -> None:
        assert evaluate_tool_availability(descriptor=_BASE_DESCRIPTOR) == []

    def test_evaluates_auth_env_config_plugin_and_context_signals_from_data_only(self) -> None:
        descriptor: ToolDescriptor = {
            **_BASE_DESCRIPTOR,
            "availability": {
                "all_of": [
                    {"kind": "auth", "provider_id": "openai"},
                    {"kind": "env", "name": "OPENAI_API_KEY"},
                    {
                        "kind": "config",
                        "path": ["plugins", "entries", "demo", "config"],
                        "check": "non-empty",
                    },
                    {"kind": "plugin-enabled", "plugin_id": "demo"},
                    {"kind": "context", "key": "channel", "equals": "telegram"},
                ]
            },
        }

        assert (
            evaluate_tool_availability(
                descriptor=descriptor,
                context={
                    "auth_provider_ids": {"openai"},
                    "env": {"OPENAI_API_KEY": "set"},
                    "config": {"plugins": {"entries": {"demo": {"config": {"mode": "local"}}}}},
                    "enabled_plugin_ids": {"demo"},
                    "values": {"channel": "telegram"},
                },
            )
            == []
        )

    def test_returns_deterministic_diagnostics_for_missing_signals(self) -> None:
        descriptor: ToolDescriptor = {
            **_BASE_DESCRIPTOR,
            "availability": {
                "all_of": [
                    {"kind": "auth", "provider_id": "openai"},
                    {"kind": "env", "name": "OPENAI_API_KEY"},
                    {
                        "kind": "config",
                        "path": ["plugins", "entries", "demo", "config"],
                        "check": "non-empty",
                    },
                    {"kind": "plugin-enabled", "plugin_id": "demo"},
                    {"kind": "context", "key": "channel", "equals": "telegram"},
                ]
            },
        }

        assert [
            entry["reason"]
            for entry in evaluate_tool_availability(
                descriptor=descriptor,
                context={
                    "auth_provider_ids": set(),
                    "env": {},
                    "config": {"plugins": {"entries": {"demo": {"config": {}}}}},
                    "enabled_plugin_ids": set(),
                    "values": {"channel": "discord"},
                },
            )
        ] == [
            "auth-missing",
            "env-missing",
            "config-missing",
            "plugin-disabled",
            "context-mismatch",
        ]

    def test_does_not_treat_credential_config_values_as_available_without_resolver(self) -> None:
        descriptor: ToolDescriptor = {
            **_BASE_DESCRIPTOR,
            "availability": {
                "kind": "config",
                "path": ["models", "providers", "openai", "apiKey"],
                "check": "available",
            },
        }

        assert [
            entry["reason"]
            for entry in evaluate_tool_availability(
                descriptor=descriptor,
                context={
                    "config": {
                        "models": {
                            "providers": {
                                "openai": {
                                    "apiKey": {
                                        "source": "env",
                                        "provider": "default",
                                        "id": "OPENAI_API_KEY",
                                    }
                                }
                            }
                        }
                    },
                    "env": {},
                },
            )
        ] == ["config-missing"]

    def test_accepts_credential_config_values_through_injected_resolver(self) -> None:
        descriptor: ToolDescriptor = {
            **_BASE_DESCRIPTOR,
            "availability": {
                "kind": "config",
                "path": ["models", "providers", "openai", "apiKey"],
                "check": "available",
            },
        }

        assert (
            evaluate_tool_availability(
                descriptor=descriptor,
                context={
                    "config": {
                        "models": {
                            "providers": {
                                "openai": {
                                    "apiKey": {
                                        "source": "env",
                                        "provider": "default",
                                        "id": "OPENAI_API_KEY",
                                    }
                                }
                            }
                        }
                    },
                    "env": {"OPENAI_API_KEY": "set"},
                    "is_config_value_available": lambda params: (
                        is_record(params["value"])
                        and params["value"].get("source") == "env"
                        and params["value"].get("provider") == "default"
                        and params["value"].get("id") == "OPENAI_API_KEY"
                    ),
                },
            )
            == []
        )

    def test_does_not_infer_env_template_strings_as_configured_credentials(self) -> None:
        descriptor: ToolDescriptor = {
            **_BASE_DESCRIPTOR,
            "availability": {
                "kind": "config",
                "path": ["models", "providers", "openai", "apiKey"],
                "check": "available",
            },
        }

        assert [
            entry["reason"]
            for entry in evaluate_tool_availability(
                descriptor=descriptor,
                context={
                    "config": {
                        "models": {"providers": {"openai": {"apiKey": "${OPENAI_API_KEY}"}}}
                    },
                    "env": {"OPENAI_API_KEY": "set"},
                },
            )
        ] == ["config-missing"]

    def test_does_not_infer_ordinary_objects_with_source_provider_id_as_credentials(self) -> None:
        descriptor: ToolDescriptor = {
            **_BASE_DESCRIPTOR,
            "availability": {
                "kind": "config",
                "path": ["tools", "example"],
                "check": "non-empty",
            },
        }

        assert (
            evaluate_tool_availability(
                descriptor=descriptor,
                context={
                    "config": {
                        "tools": {
                            "example": {
                                "source": "manual",
                                "provider": "docs",
                                "id": "readme",
                            }
                        }
                    }
                },
            )
            == []
        )

    def test_supports_any_of_availability_expressions(self) -> None:
        descriptor: ToolDescriptor = {
            **_BASE_DESCRIPTOR,
            "availability": {
                "any_of": [
                    {"kind": "auth", "provider_id": "openai"},
                    {"kind": "env", "name": "OPENAI_API_KEY"},
                    {
                        "all_of": [
                            {
                                "kind": "config",
                                "path": ["plugins", "entries", "local"],
                                "check": "non-empty",
                            },
                            {"kind": "plugin-enabled", "plugin_id": "local"},
                        ]
                    },
                ]
            },
        }

        assert (
            evaluate_tool_availability(
                descriptor=descriptor,
                context={
                    "auth_provider_ids": set(),
                    "env": {"OPENAI_API_KEY": "set"},
                    "enabled_plugin_ids": set(),
                },
            )
            == []
        )

        assert [
            entry["reason"]
            for entry in evaluate_tool_availability(
                descriptor=descriptor,
                context={
                    "auth_provider_ids": set(),
                    "env": {},
                    "enabled_plugin_ids": set(),
                },
            )
        ] == ["auth-missing", "env-missing", "config-missing", "plugin-disabled"]

    def test_surfaces_unsupported_signal_sibling_when_another_any_of_branch_is_available(
        self,
    ) -> None:
        descriptor: ToolDescriptor = {
            **_BASE_DESCRIPTOR,
            "availability": {
                "any_of": [
                    {"kind": "auth", "provider_id": "openai"},
                    {"all_of": []},
                ]
            },
        }

        assert [
            entry["reason"]
            for entry in evaluate_tool_availability(
                descriptor=descriptor,
                context={"auth_provider_ids": {"openai"}},
            )
        ] == ["unsupported-signal"]
