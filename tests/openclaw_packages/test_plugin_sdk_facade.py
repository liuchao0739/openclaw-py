"""Tests for the @openclaw/plugin-sdk package facade."""

from __future__ import annotations

from pathlib import Path

import pytest

FACADE_ROOT = Path(__file__).resolve().parents[2] / "openclaw_packages" / "plugin_sdk"

EXPECTED_FACADE_MODULES = (
    "browser_config",
    "config_runtime",
    "exec_approvals_runtime",
    "gateway_method_runtime",
    "outbound_media",
    "plugin_entry",
    "plugin_runtime",
    "provider_auth",
    "provider_auth_runtime",
    "provider_entry",
    "provider_http",
    "provider_model_shared",
    "provider_model_types",
    "provider_onboard",
    "provider_stream_shared",
    "provider_tools",
    "provider_web_search",
    "provider_web_search_config_contract",
    "runtime_doctor",
    "runtime_env",
    "secret_input",
    "security_runtime",
    "testing",
    "text_runtime",
    "video_generation",
)


def test_plugin_sdk_facade_modules_exist() -> None:
    for module_name in EXPECTED_FACADE_MODULES:
        assert (FACADE_ROOT / f"{module_name}.py").is_file()


def test_gateway_method_runtime_facade_reexports_dispatch() -> None:
    from openclaw.plugin_sdk.gateway_method_runtime import dispatch_gateway_method as core
    from openclaw_packages.plugin_sdk.gateway_method_runtime import (
        dispatch_gateway_method as facade,
    )

    assert facade is core


def test_plugin_entry_facade_reexports_define_plugin_entry() -> None:
    from openclaw.plugin_sdk.plugin_entry import define_plugin_entry as core
    from openclaw_packages.plugin_sdk.plugin_entry import define_plugin_entry as facade

    assert facade is core


def test_provider_http_facade_reexports_read_provider_text_response() -> None:
    from openclaw.plugin_sdk.provider_http import read_provider_text_response as core
    from openclaw_packages.plugin_sdk.provider_http import read_provider_text_response as facade

    assert facade is core


def test_provider_web_search_facade_reexports_resolve_timeout_seconds() -> None:
    from openclaw.plugin_sdk.provider_web_search import resolve_timeout_seconds as core
    from openclaw_packages.plugin_sdk.provider_web_search import (
        resolve_timeout_seconds as facade,
    )

    assert facade is core


def test_security_runtime_facade_reexports_redact_sensitive_text() -> None:
    from openclaw.plugin_sdk.security_runtime import redact_sensitive_text as core
    from openclaw_packages.plugin_sdk.security_runtime import redact_sensitive_text as facade

    assert facade is core


@pytest.mark.parametrize("module_name", EXPECTED_FACADE_MODULES)
def test_plugin_sdk_facade_docstring_matches_barrel_role(module_name: str) -> None:
    source = (FACADE_ROOT / f"{module_name}.py").read_text(encoding="utf-8")
    assert source.startswith('"""')
    assert "from openclaw.plugin_sdk." in source
