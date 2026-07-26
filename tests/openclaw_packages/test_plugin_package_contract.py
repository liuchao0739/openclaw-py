"""Tests for @openclaw/plugin-package-contract."""

from __future__ import annotations

from openclaw_packages.plugin_package_contract import (
    EXTERNAL_CODE_PLUGIN_REQUIRED_FIELD_PATHS,
    list_missing_external_code_plugin_field_paths,
    normalize_external_plugin_compatibility,
    validate_external_code_plugin_package_json,
)


def test_normalizes_openclaw_compatibility_block_for_external_plugins() -> None:
    assert normalize_external_plugin_compatibility(
        {
            "version": "1.2.3",
            "openclaw": {
                "compat": {
                    "pluginApi": ">=2026.3.24-beta.2",
                    "minGatewayVersion": "2026.3.24-beta.2",
                },
                "build": {
                    "openclawVersion": "2026.3.24-beta.2",
                    "pluginSdkVersion": "0.9.0",
                },
            },
        }
    ) == {
        "plugin_api_range": ">=2026.3.24-beta.2",
        "built_with_openclaw_version": "2026.3.24-beta.2",
        "plugin_sdk_version": "0.9.0",
        "min_gateway_version": "2026.3.24-beta.2",
    }


def test_falls_back_to_install_min_host_version_and_package_version() -> None:
    assert normalize_external_plugin_compatibility(
        {
            "version": "1.2.3",
            "openclaw": {
                "compat": {
                    "pluginApi": ">=1.0.0",
                },
                "install": {
                    "minHostVersion": "2026.3.24-beta.2",
                },
            },
        }
    ) == {
        "plugin_api_range": ">=1.0.0",
        "built_with_openclaw_version": "1.2.3",
        "min_gateway_version": "2026.3.24-beta.2",
    }


def test_lists_required_external_code_plugin_fields() -> None:
    assert EXTERNAL_CODE_PLUGIN_REQUIRED_FIELD_PATHS == (
        "openclaw.compat.pluginApi",
        "openclaw.build.openclawVersion",
    )


def test_reports_missing_required_fields_with_stable_field_paths() -> None:
    package_json = {
        "openclaw": {
            "compat": {},
            "build": {},
        },
    }

    assert list_missing_external_code_plugin_field_paths(package_json) == [
        "openclaw.compat.pluginApi",
        "openclaw.build.openclawVersion",
    ]
    assert validate_external_code_plugin_package_json(package_json)["issues"] == [
        {
            "field_path": "openclaw.compat.pluginApi",
            "message": "openclaw.compat.pluginApi is required for external code plugin packages.",
        },
        {
            "field_path": "openclaw.build.openclawVersion",
            "message": "openclaw.build.openclawVersion is required for external code plugin packages.",
        },
    ]
